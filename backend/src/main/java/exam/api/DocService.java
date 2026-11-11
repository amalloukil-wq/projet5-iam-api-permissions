package exam.api;

import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Donnees de test : remet la table a zero (ids 1 et 2) et la remplit au premier demarrage. */
@Service
public class DocService implements ApplicationRunner {
    private final DocRepository repo;
    private final JdbcTemplate jdbc;

    public DocService(DocRepository repo, JdbcTemplate jdbc) {
        this.repo = repo;
        this.jdbc = jdbc;
    }

    @Transactional
    public void reset() {
        jdbc.execute("TRUNCATE TABLE docs RESTART IDENTITY");
        repo.save(new Doc("Budget annuel", "amartin"));      // id 1
        repo.save(new Doc("Specification API", "bdupont"));  // id 2
    }

    @Override
    public void run(ApplicationArguments args) {
        if (repo.count() == 0) reset();
    }
}
