# Ouvre 3 fenetres PowerShell VISIBLES (une par programme), pour la demonstration :
#   - KEYCLOAK            (port 8080)
#   - API Java Spring Boot (port 8000)
#   - APPLICATION Angular  (port 4200)
# Ne pas les fermer pendant la demonstration. Ctrl+C dans une fenetre arrete son programme.
# Usage :  .\demarrage\ouvrir-fenetres-demo.ps1

$racine = Split-Path $PSScriptRoot -Parent

function Fenetre($titre, $script) {
    $cmd = "`$host.UI.RawUI.WindowTitle = '$titre'; " +
           "`$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User'); " +
           "Write-Host '=== $titre ===' -ForegroundColor Cyan; " +
           "& '$racine\demarrage\$script'"
    Start-Process powershell.exe -WorkingDirectory $racine -ArgumentList '-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $cmd
}

Fenetre 'KEYCLOAK (port 8080)' 'lancer-keycloak.ps1'
Fenetre 'API Java Spring Boot (port 8000)' 'lancer-backend.ps1'
Fenetre 'APPLICATION Angular (port 4200)' 'lancer-frontend.ps1'

Write-Host "3 fenetres ouvertes. Attendre environ 1 minute, puis lancer dans un 4e terminal :"
Write-Host "  .\.venv\Scripts\python.exe scripts\setup_keycloak.py"
