# Instrucciones de trabajo para Atlas

Antes de proponer o realizar cambios, leer `docs/project-context.md` y la
documentación relacionada con la parte afectada.

- Explicar las decisiones de forma que el usuario pueda aprender del proceso.
- Mantener la implementación pequeña y simple; no agregar dependencias sin una
  necesidad concreta.
- Aplicar pensamiento crítico: señalar riesgos, contradicciones y alternativas.
- No incorporar funciones solo porque sean interesantes; relacionarlas con un
  problema real y una forma de verificar su utilidad.
- No dividir `src/atlas/main.py` prematuramente. Hacerlo cuando exista una razón de
  mantenimiento clara.
- No versionar datos personales, especialmente `data/entries.jsonl`.
- No leer ni borrar `data/entries.jsonl` sin revisar antes su contenido: puede
  tener registros reales del usuario, no solo datos de prueba.
- Para probar Atlas manualmente (smoke test) o correr el programa de punta a
  punta, usar `ATLAS_DATA_FILE` apuntando a un archivo temporal en vez del
  real. Nunca ejecutar `main.py` de forma exploratoria contra
  `data/entries.jsonl` sin esa variable.
- Mantener la documentación en español y el código con nombres técnicos en inglés
  cuando resulte natural.
- No integrar IA, voz, servicios externos o automatizaciones sin que formen parte
  explícita del alcance aprobado.
- Antes de iniciar nuevas funciones, comprobar si Sprint 2.1 sigue pendiente.
