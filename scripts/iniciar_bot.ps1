# Arranca el bot de Telegram en segundo plano, sin ventana visible.
# Pensado para correr solo al iniciar sesion en Windows (Task Scheduler),
# como solucion provisoria mientras Atlas no tiene un equipo propio
# siempre encendido (Raspberry Pi / laptop vieja).
#
# El token NO esta en este archivo: se lee de la variable de entorno
# ATLAS_TELEGRAM_TOKEN, configurada una sola vez a nivel de usuario de
# Windows (setx), nunca escrita en ningun archivo versionado.
#
# Usa Start-Process -WindowStyle Hidden en vez de "start /min" de un .bat:
# "start /min" crea una consola nueva para el proceso minimizado y la
# redireccion de salida a un archivo no queda bien conectada a esa
# consola nueva (el log quedaba siempre vacio). Start-Process con
# -RedirectStandardOutput/-RedirectStandardError sí la conecta bien.

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location -Path $raiz

$carpetaLogs = Join-Path $raiz "logs"
if (-not (Test-Path $carpetaLogs)) {
    New-Item -ItemType Directory -Path $carpetaLogs | Out-Null
}

Start-Process `
    -FilePath (Join-Path $raiz ".venv\Scripts\python.exe") `
    -ArgumentList "-u", "src\atlas\telegram_bot.py" `
    -WorkingDirectory $raiz `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $carpetaLogs "bot.log") `
    -RedirectStandardError (Join-Path $carpetaLogs "bot.err.log")
