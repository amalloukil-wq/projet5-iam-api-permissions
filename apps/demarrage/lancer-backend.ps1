# Lance l'API Spring Boot sur http://localhost:8000. Laisser la fenetre ouverte.
# Pre-requis : PostgreSQL (service Windows) et Keycloak configure (python apps/scripts/setup_keycloak.py).
# JAVA_HOME deduit du java trouve (evite une valeur perimee dans un terminal ouvert avant l'installation)
$javaExe = (Get-Command java -ErrorAction SilentlyContinue).Source
if ($javaExe) { $env:JAVA_HOME = Split-Path (Split-Path $javaExe -Parent) -Parent }
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) "backend")
mvn -B spring-boot:run
