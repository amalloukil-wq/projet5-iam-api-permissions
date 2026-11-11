# Lance Keycloak 26.6 sur http://localhost:8080 (admin / admin) avec Java 25. Laisser la fenetre ouverte.
$kc = Join-Path $env:USERPROFILE "tools\keycloak-26.6.0"
if (-not (Test-Path $kc)) { Write-Error "Keycloak introuvable : lancez apps\demarrage\installer-outils.ps1"; exit 1 }
if (-not (Get-Command java -ErrorAction SilentlyContinue)) { Write-Error "Java introuvable : lancez apps\demarrage\installer-outils.ps1 puis rouvrez PowerShell"; exit 1 }
# JAVA_HOME deduit du java trouve (evite une valeur perimee dans un terminal ouvert avant l'installation)
$env:JAVA_HOME = Split-Path (Split-Path (Get-Command java).Source -Parent) -Parent
# Compte administrateur cree au premier demarrage (anciens et nouveaux noms de variables)
$env:KC_BOOTSTRAP_ADMIN_USERNAME = "admin"
$env:KC_BOOTSTRAP_ADMIN_PASSWORD = "admin"
$env:KEYCLOAK_ADMIN = "admin"
$env:KEYCLOAK_ADMIN_PASSWORD = "admin"
& "$kc\bin\kc.bat" start-dev
