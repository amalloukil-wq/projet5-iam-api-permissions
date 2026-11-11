# Lance le frontend Angular sur http://localhost:4200. Laisser la fenetre ouverte.
# La premiere fois, genere le projet Angular (internet requis), puis demarre le serveur.
$env:NG_CLI_ANALYTICS = "false"
$front = Join-Path (Split-Path $PSScriptRoot -Parent) "frontend"
Set-Location $front
if (-not (Test-Path "app\package.json")) { & (Join-Path $front "setup.ps1") }
Set-Location (Join-Path $front "app")
npx ng serve --port 4200
