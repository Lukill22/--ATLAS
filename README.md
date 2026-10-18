# Atlas

Atlas es un proyecto personal y modular cuyo objetivo es ayudarme a potenciar mis capacidades.
No se busca crear solo un chatbot, sino una base gradual y mantenible para evolucionar a un asistente inteligente.

## Cómo ejecutar

### Terminal (sin dependencias)

```bash
python src/atlas/main.py
```

Escribí `ayuda` dentro de Atlas para ver los comandos disponibles.

### Interfaz web local (opcional)

Usa la misma lógica que la terminal, solo cambia cómo se muestra. Necesita
Flask (`pip install -r requirements.txt`).

```bash
pip install -r requirements.txt
python src/atlas/web.py
```

Al arrancar, muestra dos direcciones: una para esta computadora
(`127.0.0.1`) y otra para abrir desde el celular en la misma wifi. **No hay
contraseña ni login**: cualquier otro dispositivo en esa misma red podría
ver y borrar los datos mientras el servidor esté corriendo — es una
decisión aceptada a propósito para una red hogareña, no un descuido. Si
alguna vez se expone más allá de la red de casa, hay que resolver
autenticación antes.

Si desde el celular no carga, puede ser el Firewall de Windows bloqueando
la conexión entrante la primera vez (suele preguntar si permitir la app).

Después abrí `http://127.0.0.1:5000/` en el navegador.

### Bot de Telegram (opcional)

Deja capturar y consultar Atlas desde un chat de Telegram, sin abrir ninguna
otra app. No usa ninguna dependencia nueva (solo `urllib`, de la librería
estándar), y no necesita ningún servidor público: consulta a Telegram cada
tanto en vez de que Telegram te llame a vos.

1. Hablale a **@BotFather** en Telegram, pedile un bot nuevo (`/newbot`), y
   guardá el token que te da.
2. Corré Atlas con ese token en una variable de entorno (nunca lo escribas
   directo en un archivo):
   ```bash
   # PowerShell
   $env:ATLAS_TELEGRAM_TOKEN = "el-token-que-te-dio-botfather"
   python src/atlas/telegram_bot.py

   # bash
   export ATLAS_TELEGRAM_TOKEN="el-token-que-te-dio-botfather"
   python src/atlas/telegram_bot.py
   ```
3. Buscá tu bot en Telegram y escribile — entiende lo mismo que la terminal
   y la web (`gasto: 15000 nafta`, `ayuda`, `listar`, `balance dia`, etc.).

**Recordatorios con alarma:** `recordatorio: 19/10 08:00 sacar la basura`
guarda un aviso para esa fecha y hora. **Solo el bot de Telegram puede
avisarte de verdad** (revisa recordatorios vencidos mientras está corriendo)
— la terminal y la web pueden crear y listar recordatorios, pero no pueden
sonar una alarma. Si el bot no estaba corriendo a esa hora, te avisa tarde
en vez de perderlo.

**Balance diario automático:** `balance diario: 23:00` configura un aviso
con el balance de hoy, todas las noches a esa hora. Es una configuración
(una por chat): mandarlo de nuevo con otra hora actualiza la que ya había
en vez de sumar una segunda. Misma limitación que los recordatorios: solo
el bot de Telegram puede avisar de verdad, y si no estaba corriendo a esa
hora, avisa tarde en vez de perderlo.

**Arranque automático (Windows, provisorio):** mientras Atlas no tiene un
equipo propio siempre encendido (ver "Decisiones abiertas" en
[docs/project-context.md](docs/project-context.md)), el bot puede arrancar
solo al iniciar sesión en Windows, sin abrir ninguna terminal:

1. Guardá el token una sola vez como variable de usuario (no hace falta
   repetirlo nunca más, ni escribirlo en ningún archivo):
   ```powershell
   setx ATLAS_TELEGRAM_TOKEN "el-token-que-te-dio-botfather"
   ```
2. Registrá la tarea programada (una sola vez):
   ```powershell
   $raiz = "C:\ruta\a\--ATLAS"  # ajustar a tu ruta real
   $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$raiz\scripts\iniciar_bot.ps1`"" -WorkingDirectory $raiz
   $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
   $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
   Register-ScheduledTask -TaskName "Atlas - Bot de Telegram" -Action $action -Trigger $trigger -Settings $settings -Force
   ```

Corre oculto (sin ventana); el log queda en `logs/bot.log` (y
`logs/bot.err.log` si algo falla). Sigue dependiendo de que la computadora
esté encendida y con la sesión iniciada — no es un reemplazo de un equipo
dedicado, solo evita tener que abrir una terminal cada vez.

Para desactivarlo: `Unregister-ScheduledTask -TaskName "Atlas - Bot de Telegram" -Confirm:$false`.

## Cómo correr las pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

## Principios de diseño

- Mantener la solución simple.
- No crear módulos innecesarios.
- No agregar dependencias sin razón clara.
- Documentar en español.
- El código puede usar nombres técnicos en inglés cuando sea útil.

## Estructura del proyecto

```text
Atlas/
├── docs/
│   ├── vision.md
│   ├── architecture.md
│   ├── project-context.md
│   ├── decisions/
│   │   └── ADR-0001-modular-architecture.md
│   └── journal/
├── src/
│   └── atlas/
│       ├── __init__.py
│       ├── main.py
│       ├── web.py
│       ├── telegram_bot.py
│       └── templates/
│           ├── index.html
│           └── confirmar_borrado.html
├── scripts/
│   └── iniciar_bot.ps1
├── tests/
│   ├── conftest.py
│   ├── test_main.py
│   ├── test_web.py
│   └── test_telegram_bot.py
├── data/
│   └── .gitkeep
├── AGENTS.md
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── requirements.txt
├── requirements-dev.txt
└── .gitignore
```

## Más información

- [ROADMAP.md](ROADMAP.md): estado de los sprints y líneas de crecimiento futuras.
- [CHANGELOG.md](CHANGELOG.md): historial de cambios por versión.
- [docs/project-context.md](docs/project-context.md): contexto completo del proyecto y forma de trabajo.
- [AGENTS.md](AGENTS.md): instrucciones de trabajo para quien (o lo que) contribuya a Atlas.
