# Annuaire LDAP DE SECOURS (a utiliser seulement si ApacheDS + Studio du TP ne sont pas disponibles).
# Memes parametres qu'ApacheDS : ldap://localhost:10389, dc=examen,dc=local, uid=admin,ou=system / secret.
# Ne pas le lancer en meme temps qu'ApacheDS (meme port). Laisser la fenetre ouverte.
# JAVA_HOME deduit du java trouve (evite une valeur perimee dans un terminal ouvert avant l'installation)
$javaExe = (Get-Command java -ErrorAction SilentlyContinue).Source
if ($javaExe) { $env:JAVA_HOME = Split-Path (Split-Path $javaExe -Parent) -Parent }
$racine = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $racine "ldap-server")
mvn -B -q compile
if ($LASTEXITCODE -ne 0) { Write-Error "Compilation impossible (reseau ? relancer)"; exit 1 }
$jar = Get-ChildItem (Join-Path $env:USERPROFILE ".m2\repository\com\unboundid\unboundid-ldapsdk") -Recurse -Filter "unboundid-ldapsdk-*.jar" |
    Select-Object -First 1
java -cp "target\classes;$($jar.FullName)" exam.ldap.LdapServer (Join-Path $racine "ldap") 10389
