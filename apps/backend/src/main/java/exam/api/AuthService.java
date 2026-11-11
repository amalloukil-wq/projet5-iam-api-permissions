package exam.api;

import com.nimbusds.jose.util.JSONObjectUtils;
import jakarta.servlet.http.HttpServletRequest;
import java.text.ParseException;
import java.time.Duration;
import java.time.Instant;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2Error;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidatorResult;
import org.springframework.security.oauth2.jwt.BadJwtException;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.JwtIssuerValidator;
import org.springframework.security.oauth2.jwt.JwtTimestampValidator;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

/**
 * Authentification et autorisation.
 *  - mode "local"      : JWT valide avec la cle publique (JWKS), sans appel reseau a chaque requete
 *  - mode "introspect" : RFC 7662, Keycloak dit si le jeton est encore actif
 * Ensuite : scope, puis role (derive des groupes LDAP).
 */
@Service
public class AuthService {

    public record Principal(String username, Set<String> scopes, Set<String> roles) {}

    // Groupes LDAP -> roles de l'API
    private static final Map<String, String> GROUP_TO_ROLE =
            Map.of("Admins", "manager", "Developers", "editor", "Staff", "reader");

    private final String issuer;
    private final String audience;
    private final NimbusJwtDecoder decoder;
    private final RestTemplate introspectionClient;
    private final String introspectUrl;
    private final Metrics metrics;

    public AuthService(@Value("${app.kc-url}") String kcUrl,
                       @Value("${app.kc-internal-url}") String kcInternalUrl,
                       @Value("${app.realm}") String realm,
                       @Value("${app.audience}") String audience,
                       @Value("${app.api-client-id}") String clientId,
                       @Value("${app.api-client-secret}") String clientSecret,
                       Metrics metrics) {
        this.metrics = metrics;
        this.audience = audience;
        // iss attendu = adresse "publique" de Keycloak (celle du navigateur) ;
        // les appels de l'API (cle publique, introspection) peuvent passer par une adresse interne (Docker : http://keycloak:8080)
        this.issuer = kcUrl + "/realms/" + realm;
        String oidc = kcInternalUrl + "/realms/" + realm + "/protocol/openid-connect";
        this.introspectUrl = oidc + "/token/introspect";

        // RestTemplate du JWKS : compte chaque telechargement de la cle publique
        RestTemplate jwksClient = new RestTemplate();
        jwksClient.getInterceptors().add((req, body, exec) -> {
            metrics.jwksFetches.incrementAndGet();
            return exec.execute(req, body);
        });
        this.decoder = NimbusJwtDecoder.withJwkSetUri(oidc + "/certs").restOperations(jwksClient).build();

        OAuth2TokenValidator<Jwt> expPresent = jwt -> jwt.getExpiresAt() == null
                ? OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "exp absent", null))
                : OAuth2TokenValidatorResult.success();
        OAuth2TokenValidator<Jwt> audValidator = jwt -> jwt.getAudience() != null && jwt.getAudience().contains(audience)
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "aud incorrect", null));
        this.decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
                new JwtTimestampValidator(Duration.ZERO),   // aucune tolerance sur exp
                new JwtIssuerValidator(issuer),
                expPresent, audValidator));

        // Client d'introspection : authentification Basic du client confidentiel "api"
        this.introspectionClient = new RestTemplate();
        this.introspectionClient.getInterceptors().add((req, body, exec) -> {
            req.getHeaders().setBasicAuth(clientId, clientSecret);
            return exec.execute(req, body);
        });
    }

    /** 401 si le jeton est absent ou invalide. */
    public Principal authenticate(HttpServletRequest req) {
        String header = req.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.regionMatches(true, 0, "Bearer ", 0, 7)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "jeton absent");
        }
        String token = header.substring(7).trim();
        String mode = req.getParameter("mode") == null ? "local" : req.getParameter("mode");

        Map<String, Object> claims;
        switch (mode) {
            case "local" -> claims = validateLocal(token);
            case "introspect" -> claims = validateIntrospection(token);
            default -> throw new ApiException(HttpStatus.BAD_REQUEST, "mode doit valoir local ou introspect");
        }

        Object pu = claims.get("preferred_username");
        String username = pu != null ? pu.toString() : String.valueOf(claims.get("sub"));
        Set<String> roles = new HashSet<>();
        if (claims.get("groups") instanceof Collection<?> groups) {
            for (Object g : groups) {
                String role = GROUP_TO_ROLE.get(String.valueOf(g));
                if (role != null) roles.add(role);
            }
        }
        if (username.startsWith("service-account-")) roles.add("service");   // tache planifiee
        Object scope = claims.get("scope");
        Set<String> scopes = scope == null ? Set.of() : new HashSet<>(List.of(scope.toString().split(" ")));
        return new Principal(username, scopes, roles);
    }

    /** 401 si non authentifie, 403 si scope ou role insuffisant. */
    public Principal require(HttpServletRequest req, String scope, Set<String> allowedRoles) {
        Principal p = authenticate(req);
        if (!p.scopes().contains(scope)) {
            throw new ApiException(HttpStatus.FORBIDDEN, "scope manquant : " + scope);
        }
        if (p.roles().stream().noneMatch(allowedRoles::contains)) {
            throw new ApiException(HttpStatus.FORBIDDEN, "role insuffisant (requis : " + allowedRoles + ")");
        }
        return p;
    }

    private Map<String, Object> validateLocal(String token) {
        try {
            return decoder.decode(token).getClaims();
        } catch (BadJwtException e) {                    // signature, exp, iss, aud, format
            throw new ApiException(HttpStatus.UNAUTHORIZED, "jeton invalide : " + e.getMessage());
        } catch (JwtException e) {                       // JWKS injoignable
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Keycloak injoignable");
        }
    }

    private Map<String, Object> validateIntrospection(String token) {
        metrics.introspectionCalls.incrementAndGet();
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("token", token);
        form.add("token_type_hint", "access_token");
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);
        Map<String, Object> data;
        try {
            String raw = introspectionClient.postForObject(introspectUrl, new HttpEntity<>(form, headers), String.class);
            if (raw == null) throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Introspection impossible");
            data = JSONObjectUtils.parse(raw);
        } catch (RestClientException | ParseException e) {
            throw new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Introspection impossible");
        }
        if (!Boolean.TRUE.equals(data.get("active"))) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "jeton inactif (introspection)");
        }
        Object aud = data.get("aud");
        List<?> audiences = aud instanceof Collection<?> c ? List.copyOf(c) : aud == null ? List.of() : List.of(aud);
        if (!issuer.equals(data.get("iss")) || !audiences.contains(audience)) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "iss ou aud incorrect");
        }
        if (!(data.get("exp") instanceof Number exp) || exp.longValue() <= Instant.now().getEpochSecond()) {
            throw new ApiException(HttpStatus.UNAUTHORIZED, "jeton expire");
        }
        return data;
    }
}
