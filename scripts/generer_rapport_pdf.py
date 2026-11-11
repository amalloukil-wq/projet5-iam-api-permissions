"""Genere le rapport d'examen complet en PDF : Rapport_Projet5.pdf (a la racine du projet).

Les chiffres (matrice, mesures, depart, revocation) sont lus dans resultats/*.md :
relancer les scripts de test puis ce script met le PDF a jour.

Usage : python scripts/generer_rapport_pdf.py
"""
import re
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph,
                                Preformatted, Spacer, Table, TableStyle)

RACINE = Path(__file__).resolve().parent.parent
RESULTATS = RACINE / "resultats"
RESULTATS_DOCKER = RACINE / "resultats-docker"
SORTIE = RACINE / "Rapport_Projet5.pdf"

# ------------------------------------------------------------------ polices (accents francais)
FONTS = Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Arial", str(FONTS / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Bold", str(FONTS / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Arial-Italic", str(FONTS / "ariali.ttf")))
pdfmetrics.registerFont(TTFont("Arial-BoldItalic", str(FONTS / "arialbi.ttf")))
registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")
pdfmetrics.registerFont(TTFont("Mono", str(FONTS / "cour.ttf")))

BLEU = colors.HexColor("#1F3A5F")
GRIS = colors.HexColor("#F2F4F7")
VERT, ORANGE, ROUGE = colors.HexColor("#2E7D32"), colors.HexColor("#EF6C00"), colors.HexColor("#C62828")

S = {
    "corps": ParagraphStyle("corps", fontName="Arial", fontSize=10, leading=14.5, alignment=TA_JUSTIFY, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=16, leading=20, textColor=BLEU, spaceBefore=14, spaceAfter=8,
                         keepWithNext=1),
    "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=12, leading=16, textColor=BLEU, spaceBefore=10, spaceAfter=5,
                         keepWithNext=1),
    "puce": ParagraphStyle("puce", fontName="Arial", fontSize=10, leading=14, leftIndent=14, bulletIndent=2, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="Arial", fontSize=8.5, leading=11),
    "cellb": ParagraphStyle("cellb", fontName="Arial-Bold", fontSize=8.5, leading=11, textColor=colors.white),
    "legende": ParagraphStyle("legende", fontName="Arial-Italic", fontSize=8.5, leading=11, alignment=TA_CENTER,
                              textColor=colors.HexColor("#555555"), spaceAfter=8),
    "titre": ParagraphStyle("titre", fontName="Arial-Bold", fontSize=26, leading=32, textColor=BLEU, alignment=TA_CENTER),
    "sous": ParagraphStyle("sous", fontName="Arial", fontSize=14, leading=19, textColor=colors.HexColor("#444444"),
                           alignment=TA_CENTER),
    "centre": ParagraphStyle("centre", fontName="Arial", fontSize=10.5, leading=16, alignment=TA_CENTER),
    "code": ParagraphStyle("code", fontName="Mono", fontSize=8.5, leading=11, backColor=GRIS, borderPadding=5,
                           leftIndent=4, spaceBefore=3, spaceAfter=8),
}


def P(t):
    return Paragraph(t, S["corps"])


def H1(t):
    return Paragraph(t, S["h1"])


def H2(t):
    return Paragraph(t, S["h2"])


def puces(items):
    return [Paragraph(i, S["puce"], bulletText="•") for i in items]


def code(t):
    return Preformatted(t, S["code"])


# ------------------------------------------------------------------ lecture des resultats
def tables_md(fichier, dossier=None):
    """Retourne la liste des tableaux Markdown d'un fichier (chaque tableau = liste de lignes de cellules)."""
    tables, courant = [], []
    for ligne in ((dossier or RESULTATS) / fichier).read_text(encoding="utf-8").splitlines():
        if ligne.strip().startswith("|"):
            cells = [c.strip() for c in ligne.strip().strip("|").split("|")]
            if all(re.fullmatch(r"-+", c) for c in cells):
                continue
            courant.append(cells)
        elif courant:
            tables.append(courant)
            courant = []
    if courant:
        tables.append(courant)
    return tables


def nombre(texte):
    return float(re.search(r"[\d.]+", texte).group())


MATRICE = tables_md("matrice.md")
BENCH = tables_md("bench.md")[0]
REVOC = tables_md("revocation.md")[0]
DEPART = tables_md("depart.md")[0]
depart_ligne1 = (RESULTATS / "depart.md").read_text(encoding="utf-8").splitlines()[0]


def depart_docker_ligne1():
    return (RESULTATS_DOCKER / "depart.md").read_text(encoding="utf-8").splitlines()[0].split(":")[-1]

delais = {r[0]: nombre(r[1]) for r in DEPART[1:]}
d_conn = delais["nouvelle connexion"]
d_refresh = delais["refresh token"]
d_local = delais["access token, validation locale"]
d_intro = delais["access token, introspection"]
d_groupe = nombre(depart_ligne1.split(":")[-1])
bench = {r[0]: [nombre(x) for x in r[1:]] for r in BENCH[1:]}
m_local, m_intro = bench["local"][2], bench["introspect"][2]
surcout = m_intro - m_local
# Une cellule de la matrice = un cas de test ; "(attendu ...)" signale un ecart
total_cas = sum(len(r) - 1 for t in MATRICE for r in t[1:])
ko = sum(1 for t in MATRICE for r in t[1:] for c in r[1:] if "attendu" in c)
conformes = total_cas - ko


# ------------------------------------------------------------------ tableaux
def tableau(donnees, largeurs, couleurs_statut=False, entete=True, taille=None):
    lignes = []
    for i, r in enumerate(donnees):
        lignes.append([Paragraph(str(c), S["cellb"] if (entete and i == 0) else S["cell"]) for c in r])
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B0B7C3")),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if entete:
        st.append(("BACKGROUND", (0, 0), (-1, 0), BLEU))
    for i in range(1 if entete else 0, len(donnees)):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0, i), (-1, i), GRIS))
        if couleurs_statut:
            for j, c in enumerate(donnees[i]):
                if j == 0:
                    continue
                couleur = {"200": VERT, "201": VERT, "401": ORANGE, "403": ROUGE}.get(str(c).split()[0])
                if couleur:
                    st.append(("BACKGROUND", (j, i), (j, i), couleur))
                    lignes[i][j] = Paragraph(f'<font color="white"><b>{c}</b></font>', S["cell"])
    t = Table(lignes, colWidths=largeurs, repeatRows=1 if entete else 0)
    t.setStyle(TableStyle(st))
    return t


# ------------------------------------------------------------------ schemas
def boite(d, x, y, w, h, titre, sous="", couleur="#DCE6F5", bord="#1F3A5F"):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=colors.HexColor(couleur), strokeColor=colors.HexColor(bord), strokeWidth=1))
    d.add(String(x + w / 2, y + h / 2 + (3 if sous else -3), titre, fontName="Arial-Bold", fontSize=8.5,
                 textAnchor="middle", fillColor=colors.HexColor("#102A43")))
    if sous:
        d.add(String(x + w / 2, y + h / 2 - 9, sous, fontName="Arial", fontSize=7, textAnchor="middle",
                     fillColor=colors.HexColor("#334E68")))


def fleche(d, x1, y1, x2, y2, texte="", dx=0, dy=4, lx=None, ly=None):
    d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#444444"), strokeWidth=1))
    import math
    a = math.atan2(y2 - y1, x2 - x1)
    p = 5
    d.add(Polygon([x2, y2, x2 - p * math.cos(a - 0.4), y2 - p * math.sin(a - 0.4),
                   x2 - p * math.cos(a + 0.4), y2 - p * math.sin(a + 0.4)],
                  fillColor=colors.HexColor("#444444"), strokeColor=colors.HexColor("#444444")))
    if texte:
        tx = lx if lx is not None else (x1 + x2) / 2 + dx
        ty = ly if ly is not None else (y1 + y2) / 2 + dy
        d.add(String(tx, ty, texte, fontName="Arial", fontSize=6.8, textAnchor="middle",
                     fillColor=colors.HexColor("#333333")))


def schema_architecture():
    d = Drawing(16.5 * cm, 7.6 * cm)
    boite(d, 5, 150, 120, 42, "Application Angular", "Code + PKCE", "#E3F2E1", "#2E7D32")
    boite(d, 5, 85, 120, 42, "Tâche planifiée (batch)", "Client Credentials", "#E3F2E1", "#2E7D32")
    boite(d, 205, 117, 120, 50, "Keycloak 26.6", "OIDC / OAuth 2.0 (realm examen)")
    boite(d, 395, 117, 120, 50, "ApacheDS (LDAP)", "dc=examen,dc=local", "#FFF3D6", "#B7791F")
    boite(d, 205, 15, 120, 45, "API Spring Boot", "Java 25 : scopes, rôles", "#F3E3F5", "#7B3F8C")
    boite(d, 395, 15, 120, 45, "PostgreSQL", "documents + propriétaire", "#F3E3F5", "#7B3F8C")
    fleche(d, 125, 171, 205, 150, "code + PKCE", dy=6)
    fleche(d, 125, 106, 205, 128, "client credentials", lx=214, ly=103)
    fleche(d, 325, 142, 395, 142, "utilisateurs, groupes", dy=5)
    fleche(d, 265, 117, 265, 60, "JWKS ou introspection", dx=44, dy=0)
    fleche(d, 140, 150, 220, 62, "jeton (Bearer)", lx=168, ly=70)
    fleche(d, 325, 38, 395, 38, "JDBC")
    return d


def graphique_depart():
    donnees = [("Nouvelle connexion", d_conn), ("Refresh token", d_refresh),
               ("Jeton : introspection", d_intro), ("Jeton : validation locale", d_local)]
    d = Drawing(16.5 * cm, 5.4 * cm)
    maxi = max(v for _, v in donnees)
    x0, largeur = 135, 330
    for i, (nom, v) in enumerate(donnees):
        y = 125 - i * 32
        d.add(String(x0 - 6, y + 6, nom, fontName="Arial", fontSize=8.5, textAnchor="end"))
        w = max(2, largeur * v / maxi)
        d.add(Rect(x0, y, w, 18, fillColor=ROUGE if "locale" in nom else VERT, strokeColor=None))
        d.add(String(x0 + w + 4, y + 5, f"{v:.1f} s", fontName="Arial-Bold", fontSize=8.5))
    d.add(Line(x0, 20, x0, 150, strokeColor=colors.HexColor("#888888")))
    d.add(String(x0 + largeur / 2, 5, "Délai entre la désactivation du compte et le refus de l'accès (secondes)",
                 fontName="Arial", fontSize=7.5, textAnchor="middle", fillColor=colors.HexColor("#444444")))
    return d


def graphique_bench():
    d = Drawing(16.5 * cm, 5.6 * cm)
    # bench[mode] = [appels API, appels Keycloak, moyenne, mediane, p95]
    series = [("Moyenne", 2), ("Médiane", 3), ("95e centile", 4)]
    maxi = max(max(v[2:5]) for v in bench.values())
    x0, hauteur = 60, 105
    for gi, (nom, idx) in enumerate(series):
        gx = x0 + gi * 150
        for mi, (mode, couleur) in enumerate([("local", VERT), ("introspect", ORANGE)]):
            v = bench[mode][idx]
            h = hauteur * v / maxi
            bx = gx + mi * 52
            d.add(Rect(bx, 25, 46, h, fillColor=couleur, strokeColor=None))
            d.add(String(bx + 23, 28 + h, f"{v:.1f}", fontName="Arial-Bold", fontSize=8, textAnchor="middle"))
        d.add(String(gx + 49, 12, nom, fontName="Arial", fontSize=8.5, textAnchor="middle"))
    d.add(Line(x0 - 8, 25, x0 + 440, 25, strokeColor=colors.HexColor("#888888")))
    d.add(Rect(330, 148, 9, 9, fillColor=VERT, strokeColor=None))
    d.add(String(343, 149, "validation locale", fontName="Arial", fontSize=8))
    d.add(Rect(330, 135, 9, 9, fillColor=ORANGE, strokeColor=None))
    d.add(String(343, 136, "introspection", fontName="Arial", fontSize=8))
    d.add(String(8, 150, "ms par requête", fontName="Arial", fontSize=7.5, fillColor=colors.HexColor("#444444")))
    return d


AVEC_CADRES_CAPTURES = False   # True : ajoute des cadres vides numerotes ou coller des captures d'ecran


def capture(numero, texte, hauteur=5.2 * cm):
    """Cadre vide a remplacer par une capture d'ecran (desactive par defaut)."""
    if not AVEC_CADRES_CAPTURES:
        return Spacer(1, 2)
    d = Drawing(16.5 * cm, hauteur)
    d.add(Rect(0, 0, 16.5 * cm, hauteur, rx=4, ry=4, fillColor=colors.HexColor("#FAFAFA"),
               strokeColor=colors.HexColor("#9AA5B1"), strokeDashArray=[4, 3], strokeWidth=1))
    d.add(String(8.25 * cm, hauteur / 2 + 4, f"Capture n°{numero}", fontName="Arial-Bold", fontSize=11,
                 textAnchor="middle", fillColor=colors.HexColor("#7B8794")))
    d.add(String(8.25 * cm, hauteur / 2 - 11, "(à insérer ici)", fontName="Arial", fontSize=9, textAnchor="middle",
                 fillColor=colors.HexColor("#7B8794")))
    return KeepTogether([d, Paragraph(f"<b>Capture n°{numero}.</b> {texte}", S["legende"])])


# ------------------------------------------------------------------ pages
def page_pied(canvas, doc):
    canvas.saveState()
    canvas.setFont("Arial", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(2 * cm, 1.2 * cm, "Projet 5 : API à permissions et départ d'un employé")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#CCCCCC"))
    canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    canvas.restoreState()


def page_vide(canvas, doc):
    pass


def couverture():
    e = [Spacer(1, 3.2 * cm), Paragraph("Projet 5", S["titre"]), Spacer(1, 6),
         Paragraph("API à permissions et départ d'un employé", S["titre"]), Spacer(1, 18),
         Paragraph("Gestion des Identités et des Accès (IAM) : Rapport d'examen", S["sous"]), Spacer(1, 1.2 * cm)]
    e.append(Paragraph("OAuth 2.0 · OpenID Connect · LDAP", S["sous"]))
    e.append(Spacer(1, 2.2 * cm))
    nom_style = ParagraphStyle("nom", fontName="Arial-Bold", fontSize=10, leading=14)
    carte = Table([[Paragraph("<b>Nom, prénom :</b>", S["centre"]), Paragraph("Amal Loukil", nom_style)],
                   [Paragraph("<b>Date :</b>", S["centre"]), "Novembre 2026"],
                   [Paragraph("<b>Durée :</b>", S["centre"]), "2 heures, travail individuel"]],
                  colWidths=[4.5 * cm, 8 * cm])
    carte.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "LEFT"), ("TOPPADDING", (0, 0), (-1, -1), 8)]))
    e += [carte, Spacer(1, 1.6 * cm)]
    e.append(Paragraph("<b>Sommaire</b>", S["centre"]))
    e.append(Paragraph("1. Contexte et objectif · 2. Architecture · 3. Modèle d'autorisation · 4. Mise en œuvre · "
                       "5. Durée des jetons et révocation · 6. Matrice de tests · 7. Protocole de départ · "
                       "8. Comparaison des deux modes · 9. Recommandation chiffrée · 10. Limites et conclusion · "
                       "Annexe : reproduire les mesures", S["centre"]))
    e.append(PageBreak())
    return e


def contenu():
    e = []
    # ---------------------------------------------------------------- 1
    e += [H1("1. Contexte et objectif"),
          P("Un jeton d'accès JWT est une preuve d'identité qui se vérifie sans interroger personne : l'API contrôle sa "
            "signature et sa date d'expiration. Cette force est aussi une faiblesse : <b>tant que le jeton n'est pas "
            "expiré, l'API l'accepte, même si la session qui l'a produit est terminée</b>. Pour une entreprise, cela "
            "pose une question concrète : <i>que reste-t-il comme accès à un employé après son départ ?</i>"),
          P("Ce projet répond en deux temps. D'abord, construire une API protégée avec des permissions fines : "
            "des <b>scopes</b> attribués au client, des <b>rôles</b> issus des groupes de l'annuaire LDAP, et une règle de "
            "<b>propriété</b> de la ressource. Ensuite, <b>mesurer</b> le délai avant que chaque accès tombe quand "
            "on retire l'employé de ses groupes puis qu'on désactive son compte, et comparer deux façons de "
            "valider un jeton : la validation locale et l'introspection (RFC 7662).")]

    # ---------------------------------------------------------------- 2
    e += [H1("2. Architecture"), schema_architecture(),
          Paragraph("Figure 1 : architecture de la solution (flèches : sens des échanges).", S["legende"]),
          P("L'annuaire contient les employés et leurs groupes. Keycloak authentifie l'utilisateur en vérifiant son mot "
            "de passe dans l'annuaire, lit ses groupes et délivre un jeton. L'application Angular obtient ce jeton par le "
            "flux <i>Authorization Code avec PKCE</i> ; la tâche planifiée l'obtient par <i>Client Credentials</i>. L'API "
            "Spring Boot reçoit le jeton dans l'en-tête <i>Authorization: Bearer</i>, le valide, applique les droits, puis "
            "lit ou écrit les documents dans PostgreSQL."),
          tableau([["Composant", "Technologie", "Rôle"],
                   ["Annuaire", "ApacheDS 2.0.0.AM26 (Apache Directory Studio 2.0.0-M17), suffixe dc=examen,dc=local, port 10389",
                    "Stocke les employés et les groupes"],
                   ["Serveur d'identité", "Keycloak 26.6.0, realm « examen »", "Authentifie, délivre les jetons"],
                   ["API", "Spring Boot 4.1.1, Java 25 (Amazon Corretto)", "Valide les jetons, applique les droits"],
                   ["Base de données", "PostgreSQL 16 (port 5433)", "Documents et propriétaire"],
                   ["Application web", "Angular (dernière version), PKCE écrit à la main", "Connexion et appels à l'API"],
                   ["Scripts", "Python 3.12", "Configuration, tests et mesures"]],
                  [3.2 * cm, 8.3 * cm, 5 * cm]),
          Spacer(1, 8),
          capture(1, "Apache Directory Studio : arbre de l'annuaire (dc=examen,dc=local, ou=People, ou=Groups)."),
          capture(2, "Console Keycloak : User federation > ldap (connexion à l'annuaire).")]

    # ---------------------------------------------------------------- 3
    e += [H1("3. Modèle d'autorisation"),
          P("Une requête est acceptée si <b>quatre conditions</b> sont réunies : le jeton est valide, il porte le scope "
            "exigé par la route, l'utilisateur a un rôle autorisé, et, pour une suppression, il est propriétaire du "
            "document (sauf s'il est manager)."),
          H2("3.1 Groupes LDAP, rôles et scopes"),
          tableau([["Groupe LDAP", "Membres", "Rôle dans l'API", "Droits"],
                   ["Admins", "amartin", "manager", "Tout lire, écrire et supprimer"],
                   ["Developers", "bdupont, cdurand", "editor", "Lire, écrire, supprimer ses propres documents"],
                   ["Staff", "les 5 employés", "reader", "Lire seulement"]],
                  [3 * cm, 3.6 * cm, 3.6 * cm, 6.3 * cm]),
          Spacer(1, 6),
          P("Les rôles ne sont pas stockés dans l'API : ils sont <b>déduits des groupes LDAP</b> présents dans le jeton "
            "(revendication <i>groups</i>). Un employé de Developers et de Staff cumule les rôles editor et reader. Les "
            "<b>scopes</b> décrivent ce que le <i>client</i> a le droit de demander : l'application web possède docs:read, "
            "docs:write et docs:delete ; la tâche planifiée seulement docs:read."),
          H2("3.2 Routes protégées"),
          tableau([["Route", "Scope requis", "Rôles autorisés", "Règle de propriété"],
                   ["GET /docs", "docs:read", "reader, editor, manager, service", "aucune"],
                   ["POST /docs", "docs:write", "editor, manager", "le créateur devient propriétaire"],
                   ["DELETE /docs/{id}", "docs:delete", "editor, manager", "un editor ne supprime que ses documents"]],
                  [3.4 * cm, 3 * cm, 5 * cm, 5.1 * cm]),
          Spacer(1, 6),
          P("<b>401</b> signifie « je ne sais pas qui vous êtes » (jeton absent, falsifié, expiré ou destiné à une autre "
            "API). <b>403</b> signifie « je sais qui vous êtes, mais vous n'avez pas le droit » (scope, rôle ou propriété "
            "insuffisants)."),
          capture(3, "Console Keycloak : Groups (Admins, Developers, Staff) et Client scopes (docs:read, docs:write, docs:delete).")]

    # ---------------------------------------------------------------- 4
    e += [H1("4. Mise en œuvre"),
          H2("4.1 L'annuaire"),
          P("Dans Apache Directory Studio, un serveur ApacheDS « Examen » héberge la partition <i>examen</i> de suffixe "
            "<i>dc=examen,dc=local</i>. Les utilisateurs sont dans <i>ou=People</i> et les groupes dans <i>ou=Groups</i> "
            "(classe <i>groupOfNames</i>, attribut <i>member</i> contenant le DN complet de chaque membre)."),
          code("dc=examen,dc=local\n"
               "├── ou=People\n"
               "│   ├── uid=amartin   (Alice Martin, CEO)\n"
               "│   ├── uid=bdupont   (Bob Dupont, Lead Developer)\n"
               "│   ├── uid=cdurand   (Clara Durand, Developer)\n"
               "│   ├── uid=dbernard  (David Bernard, Marketing Manager)\n"
               "│   └── uid=epetit    (Emma Petit, Support Engineer)\n"
               "└── ou=Groups\n"
               "    ├── cn=Admins      member: amartin\n"
               "    ├── cn=Developers  member: bdupont, cdurand\n"
               "    └── cn=Staff       member: les cinq employés"),
          P("Une contrainte du schéma LDAP : un <i>groupOfNames</i> doit contenir au moins un <i>member</i>. On ne peut donc "
            "pas retirer le dernier membre d'un groupe, ce qui a guidé le choix de l'employé qui « part » dans le "
            "protocole de départ (bdupont, car Developers a deux membres)."),
          H2("4.2 Keycloak"),
          P("Le realm <i>examen</i> contient une fédération LDAP (utilisateurs lus dans <i>ou=People</i>, groupes lus dans "
            "<i>ou=Groups</i> par un mappeur <i>group-ldap-mapper</i>) et quatre clients :"),
          tableau([["Client", "Type", "Usage", "Scopes"],
                   ["webapp", "public, Code + PKCE (S256)", "Application Angular", "docs:read, docs:write, docs:delete"],
                   ["batch", "confidentiel, Client Credentials", "Tâche planifiée", "docs:read seulement"],
                   ["api", "confidentiel", "Introspection par l'API (RFC 7662)", "aucun"],
                   ["other", "public", "Test de l'audience (sans audience api-examen)", "docs:read"]],
                  [2.2 * cm, 4.6 * cm, 5.2 * cm, 4.5 * cm]),
          Spacer(1, 6),
          P("Deux mappeurs de jeton sont ajoutés : <b>groups</b> (les groupes LDAP de l'utilisateur dans le jeton) et "
            "<b>audience</b> (valeur <i>api-examen</i>, pour que l'API refuse les jetons destinés à un autre service). La "
            "fédération est réglée en mode <i>UNSYNCED</i> (pour pouvoir désactiver un compte dans Keycloak) et sans cache "
            "(voir section 7)."),
          H2("4.3 L'API Spring Boot"),
          P("À chaque requête, l'API : (1) lit le jeton ; (2) le valide ; (3) vérifie le scope ; (4) convertit les groupes en "
            "rôles ; (5) vérifie le rôle puis la propriété. La validation du jeton existe en deux modes, choisis par le "
            "paramètre <i>?mode=</i> :"),
          *puces(["<b>Validation locale</b> : signature contrôlée avec la clé publique de Keycloak (JWKS, mise en cache), "
                  "émetteur (<i>iss</i>), audience (<i>aud</i> = api-examen) et date d'expiration (<i>exp</i>, "
                  "sans aucune tolérance). Aucun appel réseau par requête.",
                  "<b>Introspection (RFC 7662)</b> : l'API demande à Keycloak si le jeton est encore actif. Un appel à "
                  "Keycloak par requête, mais Keycloak connaît l'état réel du compte et de la session."]),
          H2("4.4 L'application Angular (Authorization Code + PKCE)"),
          P("Le flux est écrit à la main pour en montrer chaque étape : l'application génère un <i>code_verifier</i> "
            "aléatoire et son empreinte SHA-256 (<i>code_challenge</i>), redirige vers Keycloak avec un paramètre "
            "<i>state</i> (protection contre les attaques CSRF), puis échange le code reçu contre les jetons en présentant "
            "le <i>code_verifier</i>. Un code volé en chemin est donc inutilisable. La déconnexion révoque le refresh "
            "token (RFC 7009). L'interface affiche le jeton décodé, son compte à rebours et un journal coloré des "
            "réponses (200, 401, 403)."),
          capture(4, "Application Angular : connexion en amartin, jeton décodé (groupes, scopes) et GET /docs en 200."),
          capture(5, "Application Angular : connexion en epetit (groupe Staff) et POST /docs refusé en 403.")]

    # ---------------------------------------------------------------- 5
    e += [H1("5. Durée des jetons et révocation"),
          P("Le jeton d'accès dure <b>120 secondes</b>. Le refresh token fait l'objet d'une <b>rotation</b> : chaque "
            "renouvellement en émet un nouveau et l'ancien devient inutilisable (<i>Revoke Refresh Token</i> actif, "
            "réutilisation interdite). La révocation suit la RFC 7009 : on envoie le jeton à "
            "<i>/protocol/openid-connect/revoke</i>."),
          tableau([[c.replace("Revocation", "Révocation").replace("introspection", "introspection") for c in REVOC[0]]]
                  + [[c.replace("Revocation", "Révocation") for c in r] for r in REVOC[1:]],
                  [3.6 * cm, 2.6 * cm, 2.8 * cm, 3.2 * cm, 4.3 * cm]),
          Spacer(1, 6),
          P("<b>Lecture.</b> Révoquer le refresh token empêche tout renouvellement (le renouvellement répond 400), mais "
            "l'ancien jeton d'accès reste accepté en validation locale (200) : l'API ne contacte pas Keycloak. En "
            "introspection, le même jeton est refusé (401), car Keycloak sait que sa session est terminée. Révoquer le jeton "
            "d'accès lui-même produit le même contraste. <b>La révocation n'a donc d'effet immédiat que là où "
            "l'on interroge Keycloak.</b>")]

    # ---------------------------------------------------------------- 6
    e += [H1("6. Matrice de tests"),
          P(f"Chaque profil est testé sur chaque route, dans les deux modes de validation : "
            f"<b>{conformes} résultats sur {total_cas} sont conformes</b> à ce qui est attendu. Voici le mode local ; "
            f"le mode introspection donne exactement les mêmes codes."),
          tableau([[c.replace("tache planifiee", "tâche planifiée").replace("falsifie", "falsifié")
                    .replace("amartin via client 'other' (mauvaise aud)", "amartin via le client « other » (mauvaise audience)")
                    for c in r] for r in MATRICE[0]],
                  [5 * cm, 2.2 * cm, 2.3 * cm, 3.5 * cm, 3.5 * cm], couleurs_statut=True),
          Spacer(1, 6),
          *puces(["<b>amartin (manager)</b> peut tout faire, y compris supprimer le document de bdupont.",
                  "<b>bdupont (editor)</b> supprime son propre document (200) mais pas celui d'amartin (403) : règle de propriété.",
                  "<b>epetit (reader)</b> peut lire (200) mais ni écrire ni supprimer (403) : rôle insuffisant.",
                  "<b>La tâche planifiée</b> n'a que docs:read : elle lit (200) et le reste est refusé (403) car le scope manque.",
                  "<b>Mauvaise audience, jeton falsifié, absence de jeton</b> : 401, l'identité n'est pas établie."]),
          capture(6, "Terminal : python scripts/tests_matrix.py, avec la ligne « 56/56 résultats conformes »."),]

    # ---------------------------------------------------------------- 7
    e += [H1("7. Protocole de départ d'un employé"),
          P("L'employé qui part est <b>bdupont</b> (Bob Dupont, Lead Developer). Le protocole comporte deux étapes, "
            "dont on mesure l'effet sur chaque type d'accès :"),
          *puces(["<b>Étape 1 : retirer ses groupes</b> (Developers et Staff) dans l'annuaire.",
                  "<b>Étape 2 : désactiver son compte</b> dans Keycloak."]),
          H2("7.1 Effet du retrait des groupes"),
          P(f"Un <b>nouveau</b> jeton ne contient plus ses groupes après <b>{d_groupe:.1f} s</b> ; son POST /docs est refusé "
            f"(403). L'<b>ancien</b> jeton, lui, se comporte différemment selon le mode : en validation locale il porte "
            f"toujours les groupes (POST /docs : 201), alors qu'en introspection Keycloak recalcule les droits à chaque "
            f"appel et refuse (403)."),
          H2("7.2 Effet de la désactivation du compte"),
          tableau([["Accès", "Délai après la désactivation", "Explication"],
                   ["Nouvelle connexion", f"{d_conn:.1f} s", "Keycloak vérifie l'état du compte à chaque connexion"],
                   ["Refresh token", f"{d_refresh:.1f} s", "un compte désactivé ne peut plus renouveler son jeton"],
                   ["Jeton d'accès, introspection", f"{d_intro:.1f} s", "l'API demande à Keycloak, qui répond « inactif »"],
                   ["Jeton d'accès, validation locale", f"<b>{d_local:.1f} s</b>",
                    "l'API ne contacte personne : le jeton vit jusqu'à son expiration"]],
                  [5 * cm, 3.8 * cm, 7.7 * cm]),
          Spacer(1, 6), graphique_depart(),
          Paragraph("Figure 2 : délai avant que chaque accès de l'employé parti soit refusé.", S["legende"]),
          P(f"<b>Constat.</b> Après le départ, la connexion, le renouvellement et l'introspection tombent en quelques "
            f"secondes. Mais un jeton validé localement reste utilisable pendant <b>{d_local:.0f} secondes</b>, soit presque "
            f"toute sa durée de vie de 120 s. Les délais de quelques secondes des trois premières lignes dépendent de la "
            f"machine de test, peu puissante : seul l'écart d'ordre de grandeur avec la validation locale est significatif."),
          H2("7.3 Un piège : le cache de la fédération LDAP"),
          P("Lors des essais avec le réglage par défaut de Keycloak (<i>cache policy = DEFAULT</i>), le retrait d'un groupe "
            "dans l'annuaire n'était plus vu par les nouveaux jetons après un appel d'introspection : Keycloak gardait en "
            "cache l'utilisateur et ses groupes. Pour un protocole de départ, c'est dangereux, car l'employé conserve ses "
            "rôles. La correction est de régler la fédération sur <b>NO_CACHE</b> (les groupes sont relus à chaque jeton), "
            "au prix d'une requête LDAP par émission de jeton. La désactivation du compte, elle, invalide ce cache "
            "immédiatement. Ce comportement se reproduit avec l'option <i>--ldap-cache DEFAULT</i> du script de configuration."),
          capture(7, "Terminal : python scripts/depart.py, avec le tableau des délais."),]

    # ---------------------------------------------------------------- 8
    e += [H1("8. Comparaison des deux modes de validation"),
          tableau([["Mode", "Appels à l'API", "Appels à Keycloak", "Moyenne (ms)", "Médiane (ms)", "95e centile (ms)"]]
                  + [[("Validation locale" if r[0] == "local" else "Introspection")] + r[1:] for r in BENCH[1:]],
                  [3.6 * cm, 2.4 * cm, 2.8 * cm, 2.6 * cm, 2.5 * cm, 2.6 * cm]),
          Spacer(1, 6), graphique_bench(),
          Paragraph("Figure 3 : temps de réponse de l'API pour 100 requêtes, selon le mode de validation.", S["legende"]),
          tableau([["Critère", "Validation locale", "Introspection"],
                   ["Délai de révocation", f"jusqu'à l'expiration du jeton (mesuré : {d_local:.0f} s)",
                    f"quelques secondes (mesuré : {d_intro:.1f} s)"],
                   ["Appels à Keycloak", "0 par requête (la clé publique est mise en cache)", "1 par requête"],
                   ["Temps de réponse moyen", f"{m_local:.1f} ms", f"{m_intro:.1f} ms (+{surcout:.1f} ms, +{surcout / m_local * 100:.0f} %)"],
                   ["Dépendance à Keycloak", "faible : l'API fonctionne même s'il est indisponible",
                    "forte : si Keycloak est en panne, l'API ne peut plus valider"]],
                  [4 * cm, 6.2 * cm, 6.3 * cm]),
          Spacer(1, 6),
          P(f"L'introspection coûte environ <b>{surcout:.0f} ms de plus</b> par requête et fait peser sur Keycloak une charge "
            f"proportionnelle au trafic de l'API. En échange, elle réduit la fenêtre d'exposition d'un employé parti de "
            f"{d_local:.0f} s à {d_intro:.0f} s environ."),
          capture(8, "Terminal : python scripts/bench.py et python scripts/revocation.py.")]

    # ---------------------------------------------------------------- 9
    e += [H1("9. Recommandation chiffrée"),
          P("Le compromis tient en une phrase : <b>un jeton court réduit l'exposition mais multiplie les renouvellements ; "
            "l'introspection supprime presque l'exposition mais coûte un appel par requête</b>. Avec la validation "
            "locale, la fenêtre maximale d'accès d'un employé parti est égale à la durée de vie du jeton."),
          tableau([["Niveau de risque", "Exemples", "Durée du jeton", "Mode", "Exposition maximale après un départ"],
                   ["Faible", "lecture de données publiques", "15 minutes", "local", "15 minutes"],
                   ["Moyen", "données internes de l'entreprise", "5 minutes", "local", "5 minutes"],
                   ["Élevé", "RH, finance, suppression de données", "1 à 2 minutes",
                    "introspection (ou local avec jeton très court)", f"environ {d_intro:.0f} secondes (introspection)"]],
                  [2.4 * cm, 4 * cm, 2.6 * cm, 3.6 * cm, 3.9 * cm]),
          Spacer(1, 6),
          P(f"<b>Justification chiffrée.</b> (1) Aujourd'hui, avec un jeton de 120 s en validation locale, l'exposition "
            f"mesurée est de {d_local:.0f} s ; passer à 15 minutes la porterait à 900 s, soit environ "
            f"{900 / d_local:.0f} fois plus. (2) L'introspection ajoute {surcout:.0f} ms par requête : pour une API qui "
            f"traite 50 requêtes par seconde, cela représente 50 appels par seconde vers Keycloak, contre un "
            f"renouvellement tous les 120 s par utilisateur en validation locale. (3) On réserve donc l'introspection aux "
            f"opérations sensibles, et on garde la validation locale, rapide et indépendante, pour le reste.")]

    # ---------------------------------------------------------------- 10
    e += [H1("10. Limites et conclusion"),
          H2("Limites"),
          *puces(["Le flux « Direct Access Grant » du client webapp sert uniquement à automatiser les tests ; en production "
                  "seul le flux Code + PKCE devrait rester actif.",
                  "Les routes /_reset et /metrics et le paramètre ?mode= de l'API sont réservés à la démonstration et ne "
                  "doivent jamais être exposés.",
                  "Les comptes de test partagent un mot de passe d'exercice, et le chiffrement LDAPS est désactivé "
                  "(environnement local).",
                  "Les mesures sont faites sur une seule machine, peu puissante : les délais de quelques secondes sont "
                  "indicatifs ; l'ordre de grandeur (secondes contre durée de vie du jeton) est, lui, significatif.",
                  "Un seul employé et un seul scénario de départ ont été mesurés."]),
          H2("Conclusion"),
          P(f"Le projet montre qu'<b>authentifier n'est pas révoquer</b>. Les permissions fines (scopes, rôles issus de "
            f"l'annuaire, propriété de la ressource) donnent à chaque profil exactement les droits prévus : {conformes} "
            f"cas sur {total_cas} sont conformes. Mais la qualité d'un protocole de départ dépend surtout de la façon "
            f"dont l'API valide les jetons : en validation locale, un employé parti garde son accès pendant presque toute "
            f"la durée du jeton ({d_local:.0f} s mesurées) ; en introspection, l'accès est coupé en quelques secondes "
            f"({d_intro:.1f} s), pour un surcoût d'environ {surcout:.0f} ms par requête. Il faut enfin penser aux caches : "
            f"celui de la fédération LDAP peut masquer le retrait d'un groupe. La bonne configuration associe une durée de "
            f"jeton proportionnée au risque, l'introspection pour les opérations sensibles, un cache désactivé sur les "
            f"groupes et la désactivation du compte en dernière étape du départ.")]

    # ---------------------------------------------------------------- annexe Docker
    if (RESULTATS_DOCKER / "depart.md").exists():
        dd = {r[0]: nombre(r[1]) for r in tables_md("depart.md", RESULTATS_DOCKER)[0][1:]}
        db = {r[0]: [nombre(x) for x in r[1:]] for r in tables_md("bench.md", RESULTATS_DOCKER)[0][1:]}
        dmat = tables_md("matrice.md", RESULTATS_DOCKER)
        dcas = sum(len(r) - 1 for t in dmat for r in t[1:])
        dko = sum(1 for t in dmat for r in t[1:] for c in r[1:] if "attendu" in c)
        e += [H1("Annexe : exécution dans Docker"),
              P("Le projet complet (annuaire, base de données, Keycloak, API et application) se lance aussi dans des "
                "conteneurs avec <b>une seule commande</b> : <i>docker compose up -d --build</i> (mode d'emploi dans "
                "README-DOCKER.md). Dans ce mode, l'annuaire est <b>OpenLDAP</b>, avec les mêmes fichiers LDIF que "
                "l'ApacheDS du reste du projet (mêmes employés, mêmes groupes, même suffixe). Les jetons portent "
                "<i>iss = http://localhost:8080</i>, alors que les conteneurs joignent Keycloak par "
                "<i>http://keycloak:8080</i> : l'API distingue donc l'adresse publique (contrôle de l'émetteur) de "
                "l'adresse interne (clé publique et introspection)."),
              P(f"Les mêmes tests donnent <b>{dcas - dko} résultats conformes sur {dcas}</b>. Mesures du protocole de "
                f"départ et de la comparaison des modes dans cet environnement :"),
              tableau([["Mesure (Docker, OpenLDAP)", "Valeur"],
                       ["Nouveau jeton sans groupe après le retrait", f"{nombre(depart_docker_ligne1()):.1f} s"],
                       ["Nouvelle connexion après désactivation", f"{dd['nouvelle connexion']:.1f} s"],
                       ["Refresh token après désactivation", f"{dd['refresh token']:.1f} s"],
                       ["Jeton, introspection", f"{dd['access token, introspection']:.1f} s"],
                       ["Jeton, <b>validation locale</b>", f"<b>{dd['access token, validation locale']:.1f} s</b>"],
                       ["Temps de réponse moyen, validation locale", f"{db['local'][2]:.1f} ms"],
                       ["Temps de réponse moyen, introspection", f"{db['introspect'][2]:.1f} ms"]],
                      [10 * cm, 6.5 * cm]),
              P("Même constat qu'avec ApacheDS : la validation locale garde l'accès presque toute la durée de vie du "
                "jeton, l'introspection le coupe presque immédiatement (les écarts de quelques secondes dépendent de "
                "la machine).")]

    # ---------------------------------------------------------------- annexe
    e += [H1("Annexe : reproduire les mesures"),
          P("Ordre de lancement : serveur ApacheDS dans Studio (<i>Run</i>), Keycloak, configuration de Keycloak, API, "
            "application Angular. Puis, dans un terminal avec l'environnement Python activé :"),
          code("python scripts/preparer_ldap.py       # charge les 10 entrées dans l'annuaire\n"
               "python scripts/setup_keycloak.py      # configure Keycloak (realm, clients, scopes, LDAP)\n"
               "python scripts/tests_matrix.py        # matrice 200/201/401/403 (56 cas)\n"
               "python scripts/bench.py               # validation locale contre introspection\n"
               "python scripts/revocation.py          # révocation RFC 7009\n"
               "python scripts/depart.py              # protocole de départ, délais mesurés\n"
               "python scripts/generer_rapport_pdf.py # régénère ce document avec les derniers chiffres"),
          P("Comptes de test (mot de passe <i>secret</i>) : <b>amartin</b> (manager), <b>bdupont</b> (editor), "
            "<b>epetit</b> (reader). Console Keycloak : http://localhost:8080 (admin / admin). Application : "
            "http://localhost:4200.")]
    return e


def main():
    doc = BaseDocTemplate(str(SORTIE), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                          bottomMargin=2.2 * cm, title="Projet 5 : API à permissions et départ d'un employé",
                          author="Amal Loukil", subject="Gestion des Identités et des Accès (IAM)")
    cadre = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="n")
    doc.addPageTemplates([PageTemplate(id="couv", frames=[cadre], onPage=page_vide, autoNextPageTemplate="corps"),
                          PageTemplate(id="corps", frames=[cadre], onPage=page_pied)])
    doc.build(couverture() + contenu())
    print(f"PDF genere : {SORTIE}  ({SORTIE.stat().st_size / 1024:.0f} Ko)")


if __name__ == "__main__":
    main()
