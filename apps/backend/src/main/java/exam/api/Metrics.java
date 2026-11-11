package exam.api;

import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Component;

/** Compteurs d'appels a Keycloak (pour comparer validation locale et introspection). */
@Component
public class Metrics {
    public final AtomicInteger jwksFetches = new AtomicInteger();
    public final AtomicInteger introspectionCalls = new AtomicInteger();
}
