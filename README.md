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
Flask (`pip install -r requirements.txt`) y corre solo en tu propia
computadora (`127.0.0.1`), nunca expuesta a la red.

```bash
pip install -r requirements.txt
python src/atlas/web.py
```

Después abrí `http://127.0.0.1:5000/` en el navegador.

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
│       └── templates/
│           ├── index.html
│           └── confirmar_borrado.html
├── tests/
│   ├── conftest.py
│   ├── test_main.py
│   └── test_web.py
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
