package exam.api;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import java.util.Set;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * Modele d'autorisation :
 *   GET    /docs      scope docs:read    roles reader, editor, manager, service
 *   POST   /docs      scope docs:write   roles editor, manager
 *   DELETE /docs/{id} scope docs:delete  roles editor, manager ; un editor ne supprime que ses documents
 */
@RestController
public class DocController {

    public record NewDoc(String title) {}

    private final AuthService auth;
    private final DocRepository repo;
    private final DocService docService;
    private final Metrics metrics;

    public DocController(AuthService auth, DocRepository repo, DocService docService, Metrics metrics) {
        this.auth = auth;
        this.repo = repo;
        this.docService = docService;
        this.metrics = metrics;
    }

    @GetMapping("/docs")
    public Map<String, Object> list(HttpServletRequest req) {
        AuthService.Principal p = auth.require(req, "docs:read", Set.of("reader", "editor", "manager", "service"));
        return Map.of("user", p.username(), "roles", p.roles().stream().sorted().toList(),
                "docs", repo.findAll(Sort.by("id")));
    }

    @PostMapping("/docs")
    public ResponseEntity<Doc> create(HttpServletRequest req, @RequestBody NewDoc body) {
        AuthService.Principal p = auth.require(req, "docs:write", Set.of("editor", "manager"));
        if (body == null || body.title() == null || body.title().isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "title obligatoire");
        }
        return ResponseEntity.status(HttpStatus.CREATED).body(repo.save(new Doc(body.title(), p.username())));
    }

    @DeleteMapping("/docs/{id}")
    public Map<String, Object> delete(HttpServletRequest req, @PathVariable long id) {
        AuthService.Principal p = auth.require(req, "docs:delete", Set.of("editor", "manager"));
        Doc doc = repo.findById(id).orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "document introuvable"));
        if (!p.roles().contains("manager") && !doc.getOwner().equals(p.username())) {
            throw new ApiException(HttpStatus.FORBIDDEN, "vous n'etes pas proprietaire de ce document");
        }
        repo.delete(doc);
        return Map.of("deleted", id);
    }

    // ---- outils de demonstration (non proteges, a ne jamais exposer en production) ----
    @PostMapping("/_reset")
    public Map<String, Object> reset() {
        docService.reset();
        return Map.of("ok", true);
    }

    @GetMapping("/metrics")
    public Map<String, Integer> metrics() {
        return Map.of("jwks_fetches", metrics.jwksFetches.get(),
                "introspection_calls", metrics.introspectionCalls.get());
    }
}
