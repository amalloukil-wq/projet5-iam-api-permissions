package exam.ldap;

import com.unboundid.ldap.listener.InMemoryDirectoryServer;
import com.unboundid.ldap.listener.InMemoryDirectoryServerConfig;
import com.unboundid.ldap.listener.InMemoryListenerConfig;
import java.io.File;

/**
 * Annuaire LDAP de SECOURS en memoire, avec les memes parametres que l'ApacheDS de Studio :
 *   ldap://localhost:10389, suffixe dc=examen,dc=local, administrateur uid=admin,ou=system / secret.
 * Charge base.ldif, users.ldif et groups.ldif du dossier ldap/. Les modifications sont perdues a l'arret.
 * A utiliser seulement si ApacheDS + Studio ne sont pas disponibles : le reste du projet ne voit aucune difference.
 *
 * Usage : LdapServer [dossier des ldif] [port]
 */
public class LdapServer {
    public static void main(String[] args) throws Exception {
        String dir = args.length > 0 ? args[0] : "../ldap";
        int port = args.length > 1 ? Integer.parseInt(args[1]) : 10389;

        InMemoryDirectoryServerConfig cfg = new InMemoryDirectoryServerConfig("dc=examen,dc=local");
        cfg.addAdditionalBindCredentials("uid=admin,ou=system", "secret");
        cfg.setListenerConfigs(InMemoryListenerConfig.createLDAPConfig("default", port));

        InMemoryDirectoryServer server = new InMemoryDirectoryServer(cfg);
        server.add("dn: dc=examen,dc=local", "objectClass: top", "objectClass: domain", "dc: examen");
        for (String f : new String[] {"base.ldif", "users.ldif", "groups.ldif"}) {
            server.importFromLDIF(false, new File(dir, f).getPath());
        }
        server.startListening();

        System.out.println("LDAP de secours pret sur ldap://localhost:" + port + " (dc=examen,dc=local, "
                + server.countEntries() + " entrees). Ctrl+C pour arreter.");
        Thread.currentThread().join();
    }
}
