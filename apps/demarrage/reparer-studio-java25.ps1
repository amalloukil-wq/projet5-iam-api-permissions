# Permet au serveur ApacheDS de Studio M17 de demarrer avec Java 25 (le TP exigeait Java 11).
#
# Deux causes, deux corrections :
#  1. ApacheDS 2.0.0-AM26 utilise une classe interne de Java (sun.security.x509) que Java 17+ protege :
#     on la rend accessible avec --add-exports, passe aux programmes lances par Studio via JAVA_TOOL_OPTIONS.
#  2. ApacheDS essaie de fabriquer lui-meme un certificat avec une fonction interne qui n'existe plus en Java 25 :
#     on lui fournit un fichier de cles (cree avec keytool) et on desactive LDAPS / StartTLS (inutiles ici).
#
# Usage : .\demarrage\reparer-studio-java25.ps1
#   - ferme Studio s'il est ouvert, corrige TOUS les serveurs deja crees dans Studio, puis relance Studio.
#   - a relancer apres avoir cree un nouveau serveur dans Studio (puis cliquer sur Run).

$ErrorActionPreference = "Stop"
$studio = Join-Path $env:USERPROFILE "tools\ApacheDirectoryStudio\ApacheDirectoryStudio\ApacheDirectoryStudio.exe"
$serversRoot = Join-Path $env:USERPROFILE ".ApacheDirectoryStudio\.metadata\.plugins\org.apache.directory.studio.ldapservers\servers"
if (-not (Test-Path $studio)) { Write-Error "Studio introuvable : $studio"; exit 1 }

# Java : JAVA_HOME deduit du java trouve
$javaExe = (Get-Command java -ErrorAction SilentlyContinue).Source
if (-not $javaExe) { Write-Error "Java introuvable : rouvrez PowerShell apres installer-outils.ps1"; exit 1 }
$javaHome = Split-Path (Split-Path $javaExe -Parent) -Parent
$keytool = Join-Path $javaHome "bin\keytool.exe"

# 1. Fermer Studio (il reecrit sa configuration a la fermeture)
$running = Get-Process ApacheDirectoryStudio -ErrorAction SilentlyContinue
if ($running) { Write-Host "Fermeture de Studio..."; $running | Stop-Process -Force; Start-Sleep 3 }

# 2. Corriger chaque serveur
$utf8 = New-Object System.Text.UTF8Encoding($false)
function Long($p) { "\\?\" + $p }                      # chemins > 260 caracteres
$n = 0
if (Test-Path $serversRoot) {
  foreach ($srv in Get-ChildItem $serversRoot -Directory) {
    $conf = Join-Path $srv.FullName "conf"
    if (-not (Test-Path (Join-Path $conf "ou=config"))) { continue }
    $n++
    Write-Host "Serveur $($srv.Name) :"

    $ks = Join-Path $conf "ads.keystore"
    if (-not (Test-Path $ks)) {
      # keytool ecrit sa progression sur stderr : on verifie le resultat par le fichier cree
      $ErrorActionPreference = "Continue"
      & $keytool -genkeypair -alias apacheds -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=localhost" `
          -keystore $ks -storepass secret -keypass secret -storetype PKCS12 2>&1 | Out-Null
      $ErrorActionPreference = "Stop"
      if (-not (Test-Path $ks)) { Write-Error "keytool n'a pas cree le fichier de cles"; exit 1 }
      Write-Host "  fichier de cles cree"
    }

    $ldapDir = Join-Path $conf "ou=config\ads-directoryserviceid=default\ou=servers"
    $f = Join-Path $ldapDir "ads-serverid=ldapserver.ldif"
    $t = [IO.File]::ReadAllText((Long $f))
    if ($t -notmatch "ads-keystoreFile") {
      $path = $ks.Replace("\", "/")
      $t = $t.TrimEnd() + "`nads-keystoreFile: $path`nads-certificatePassword: secret`n"
      [IO.File]::WriteAllText((Long $f), $t, $utf8)
      Write-Host "  fichier de cles declare dans la configuration"
    }
    foreach ($rel in "ads-serverid=ldapserver\ou=transports\ads-transportid=ldaps.ldif",
                     "ads-serverid=ldapserver\ou=extendedophandlers\ads-extendedopid=starttlshandler.ldif") {
      $g = Join-Path $ldapDir $rel
      if (Test-Path (Long $g)) {
        $x = [IO.File]::ReadAllText((Long $g))
        if ($x -match "ads-enabled: TRUE") { [IO.File]::WriteAllText((Long $g), $x.Replace("ads-enabled: TRUE", "ads-enabled: FALSE"), $utf8) }
      }
    }
    Remove-Item (Join-Path $srv.FullName ".dirservice.lock") -Force -ErrorAction SilentlyContinue
    Write-Host "  LDAPS et StartTLS desactives"
  }
}
if ($n -eq 0) { Write-Host "Aucun serveur cree pour l'instant : creez-le dans Studio, puis relancez ce script." }

# 3. Relancer Studio avec l'option Java, que le serveur ApacheDS heritera
$env:JAVA_HOME = $javaHome
$env:Path = "$javaHome\bin;$env:Path"
# Attention : dans JAVA_TOOL_OPTIONS la forme est --add-exports=module/paquet=cible (avec "=", sans espace)
$env:JAVA_TOOL_OPTIONS = "--add-exports=java.base/sun.security.x509=ALL-UNNAMED"
Start-Process $studio -WorkingDirectory (Split-Path $studio)
Write-Host "`nStudio relance. Dans l'onglet LDAP Servers : clic droit sur le serveur > Run (Executer)."
