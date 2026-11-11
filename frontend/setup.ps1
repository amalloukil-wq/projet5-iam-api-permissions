# Cree le projet Angular (derniere version) dans frontend\app puis y copie nos fichiers.
# Pre-requis : Node.js 22.12+ (https://nodejs.org).  Usage : .\setup.ps1
$env:NG_CLI_ANALYTICS = "false"
Set-Location $PSScriptRoot

if (-not (Test-Path "app\package.json")) {
    # npm ecrit sa progression sur stderr : on verifie le code de retour plutot que ce flux
    npx --yes "@angular/cli@latest" new app --routing=false --style=css --skip-git --skip-tests --ssr=false --defaults
    if ($LASTEXITCODE -ne 0) { Write-Error "ng new a echoue (code $LASTEXITCODE)"; exit 1 }
}
# Nos fichiers remplacent ceux generes ; on retire l'ancien composant s'il existe (anciennes versions du CLI)
Remove-Item "app\src\app\app.component.*" -Force -ErrorAction SilentlyContinue
Copy-Item "overrides\src\*" "app\src\" -Recurse -Force
Write-Host "`nOK. Lancer le frontend :  cd app ; npm start   puis ouvrir http://localhost:4200"
