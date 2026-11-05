# Arranca la interfaz web en segundo plano, sin ventana visible.
# Mismo mecanismo que iniciar_bot.ps1 (ver los comentarios de ese archivo):
# pensado para correr solo al iniciar sesion en Windows (Task Scheduler).
#
# La web escucha en la red local y no tiene contrasena: mientras esto este
# corriendo, cualquiera en la misma wifi puede ver y borrar los datos.

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location -Path $raiz

$carpetaLogs = Join-Path $raiz "logs"
if (-not (Test-Path $carpetaLogs)) {
    New-Item -ItemType Directory -Path $carpetaLogs | Out-Null
}

Start-Process `
    -FilePath (Join-Path $raiz ".venv\Scripts\python.exe") `
    -ArgumentList "-u", "src\atlas\web.py" `
    -WorkingDirectory $raiz `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $carpetaLogs "web.log") `
    -RedirectStandardError (Join-Path $carpetaLogs "web.err.log")
