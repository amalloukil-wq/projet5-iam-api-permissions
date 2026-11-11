package exam.api;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Document stocke dans PostgreSQL ; "owner" sert a la regle de propriete. */
@Entity
@Table(name = "docs")
public class Doc {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String title;
    private String owner;

    protected Doc() {}

    public Doc(String title, String owner) {
        this.title = title;
        this.owner = owner;
    }

    public Long getId() { return id; }
    public String getTitle() { return title; }
    public String getOwner() { return owner; }
}
