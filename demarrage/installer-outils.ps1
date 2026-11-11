# Installe tous les outils necessaires (sans Docker) :
#   JDK 25 (une seule version de Java pour backend, Keycloak et annuaire de secours),
#   Node 22 (Angular), Python 3.12 (scripts), PostgreSQL 16 (port 5433), Maven, Keycloak 26.6.0.
# Usage : .\demarrage\installer-outils.ps1
# Une ou deux fenetres d'autorisation administrateur peuvent apparaitre : cliquer sur Oui.
# Si le reseau coupe, relancer le script : ce qui est deja installe est ignore.

$ErrorActionPreference = "Continue"
$tools = Join-Path $env:USERPROFILE "tools"
New-Item -ItemType Directory -Force $tools | Out-Null
$resume = @()

function Install-Winget($id, $name, $override) {
    $already = winget list --id $id --exact 2>$null | Select-String $id
    if ($already) { Write-Host "[ok] $name deja installe"; return }
    Write-Host "== Installation de $name =="
    $args = @("install", "--id", $id, "--exact", "--source", "winget", "--silent",
              "--accept-package-agreements", "--accept-source-agreements")
    if ($override) { $args += @("--override", $override) }
    & winget @args
    if ($LASTEXITCODE -ne 0) { $script:resume += $name; Write-Warning "$name : echec (code $LASTEXITCODE)" }
}

function Download($url, $dest) {
    # curl reprend un telechargement interrompu (-C -) et reessaie en cas de coupure
    curl.exe -L -C - --retry 30 --retry-delay 4 --retry-all-errors --connect-timeout 20 -o $dest $url
    return ($LASTEXITCODE -eq 0 -and (Test-Path $dest))
}

# Amazon Corretto 25 (OpenJDK gratuit) : telechargeable meme quand GitHub (Temurin) est bloque
Install-Winget "Amazon.Corretto.25.JDK" "JDK 25 (Amazon Corretto)"
Install-Winget "OpenJS.NodeJS.22" "Node.js 22"
Install-Winget "Python.Python.3.12" "Python 3.12"
Install-Winget "PostgreSQL.PostgreSQL.16" "PostgreSQL 16" "--mode unattended --unattendedmodeui none --superpassword postgres --serverport 5433"

# --- Base de donnees ---
$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (Test-Path $psql) {
    $env:PGPASSWORD = "postgres"
    & $psql -h localhost -p 5433 -U postgres -c "CREATE USER docs WITH PASSWORD 'docs';" 2>$null | Out-Null
    & $psql -h localhost -p 5433 -U postgres -c "CREATE DATABASE docs OWNER docs;" 2>$null | Out-Null
    $env:PGPASSWORD = "docs"
    $test = & $psql -h localhost -p 5433 -U docs -d docs -tAc "select 1" 2>$null
    if ($test -eq "1") { Write-Host "[ok] base 'docs' prete (utilisateur docs / mot de passe docs)" }
    else { $resume += "base PostgreSQL docs"; Write-Warning "base 'docs' non creee" }
}

# --- Maven ---
$mvnDir = Get-ChildItem $tools -Directory -Filter "apache-maven-*" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mvnDir) {
    Write-Host "== Installation de Maven =="
    try {
        $idx = (Invoke-WebRequest "https://dlcdn.apache.org/maven/maven-3/" -UseBasicParsing -TimeoutSec 30).Content
        $v = ([regex]::Matches($idx, 'href="(3\.9\.\d+)/"') | ForEach-Object { [version]$_.Groups[1].Value } | Sort-Object -Descending | Select-Object -First 1).ToString()
        $url = "https://dlcdn.apache.org/maven/maven-3/$v/binaries/apache-maven-$v-bin.zip"
        $zip = Join-Path $tools "maven.zip"
        if (Download $url $zip) {
            $expected = ((Invoke-WebRequest "$url.sha512" -UseBasicParsing).Content.Trim() -split "\s+")[0].ToLower()
            $actual = (Get-FileHash $zip -Algorithm SHA512).Hash.ToLower()
            if ($actual -eq $expected) { Expand-Archive $zip -DestinationPath $tools -Force; Remove-Item $zip }
            else { Remove-Item $zip -Force; throw "empreinte SHA-512 incorrecte (telechargement corrompu)" }
        } else { throw "telechargement impossible" }
    } catch { $resume += "Maven"; Write-Warning "Maven : $($_.Exception.Message)" }
    $mvnDir = Get-ChildItem $tools -Directory -Filter "apache-maven-*" -ErrorAction SilentlyContinue | Select-Object -First 1
}
if ($mvnDir) {
    $bin = Join-Path $mvnDir.FullName "bin"
    $p = [Environment]::GetEnvironmentVariable("Path", "User")
    if (($p -split ";") -notcontains $bin) { [Environment]::SetEnvironmentVariable("Path", ($p.TrimEnd(";") + ";" + $bin), "User") }
    Write-Host "[ok] Maven : $($mvnDir.FullName)"
}

# --- Keycloak ---
$kc = Join-Path $tools "keycloak-26.6.0"
if (-not (Test-Path (Join-Path $kc "bin\kc.bat"))) {
    Write-Host "== Installation de Keycloak 26.6.0 (environ 170 Mo, depuis Maven Central) =="
    $zip = Join-Path $tools "keycloak.zip"
    if (Download "https://repo.maven.apache.org/maven2/org/keycloak/keycloak-quarkus-dist/26.6.0/keycloak-quarkus-dist-26.6.0.zip" $zip) {
        try {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            [IO.Compression.ZipFile]::OpenRead($zip).Dispose()   # echoue si le zip est incomplet
            Expand-Archive $zip -DestinationPath $tools -Force
            Remove-Item $zip
        } catch { Remove-Item $zip -Force; $resume += "Keycloak"; Write-Warning "Keycloak : zip incomplet, relancer le script" }
    } else { $resume += "Keycloak"; Write-Warning "Keycloak : telechargement impossible" }
}
if (Test-Path (Join-Path $kc "bin\kc.bat")) { Write-Host "[ok] Keycloak : $kc" }

Write-Host ""
if ($resume.Count -eq 0) { Write-Host "TERMINE : tout est installe. Fermez puis rouvrez PowerShell." -ForegroundColor Green }
else { Write-Host "INCOMPLET, a relancer : $($resume -join ', ')" -ForegroundColor Yellow }
