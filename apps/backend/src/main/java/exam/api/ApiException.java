package exam.api;

import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/** Erreur HTTP metier (401, 403, 404, 503...). */
public class ApiException extends RuntimeException {
    private final HttpStatus status;

    public ApiException(HttpStatus status, String message) {
        super(message);
        this.status = status;
    }

    public HttpStatus getStatus() {
        return status;
    }

    @RestControllerAdvice
    public static class Handler {
        @ExceptionHandler(ApiException.class)
        public ResponseEntity<Map<String, String>> handle(ApiException e) {
            ResponseEntity.BodyBuilder b = ResponseEntity.status(e.getStatus());
            if (e.getStatus() == HttpStatus.UNAUTHORIZED) {
                b.header(HttpHeaders.WWW_AUTHENTICATE, "Bearer");
            }
            return b.body(Map.of("detail", e.getMessage()));
        }
    }
}
