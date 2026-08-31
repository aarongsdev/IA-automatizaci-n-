# APPLY_INSTRUCTIONS.md
## Cómo aplicar este paquete sobre MoneyPrinterTurbo

Este .zip contiene **solo los archivos nuevos o modificados**, no el repositorio entero (el original pesa ~200MB por sus fuentes/música incluidas, y no hace falta que ese peso pase por aquí — GitHub lo copia solo al hacer el fork).

### Pasos

1. Ve a [github.com/harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) y pulsa **Fork** (arriba a la derecha). Esto crea una copia completa en tu cuenta de GitHub en segundos, sin que tengas que subir ni descargar nada tú.
2. Recomendado: en la configuración del fork, dale visibilidad **pública** (ver el porqué en `README_ADAPTACION.md`, sección "1. Crea el repositorio").
3. Clona TU fork a tu ordenador (o usa el editor web de GitHub, funciona igual para archivos de texto):
   ```bash
   git clone https://github.com/TU-USUARIO/MoneyPrinterTurbo.git
   cd MoneyPrinterTurbo
   ```
4. Copia dentro de esa carpeta todos los archivos de este .zip **respetando las mismas rutas** (sobrescribe `app/services/task.py` y `config.example.toml`, añade los demás como archivos nuevos):
   ```
   app/services/task.py                        → SOBRESCRIBE
   app/services/official_publish.py             → NUEVO
   app/services/github_asset_host.py             → NUEVO
   config.example.toml                          → SOBRESCRIBE
   scripts/pick_topic.py                        → NUEVO
   scripts/publish_video.py                     → NUEVO
   scripts/render_config.py                     → NUEVO
   content/topics_queue.txt                     → NUEVO
   .github/workflows/daily_episode.yml          → NUEVO
   README_ADAPTACION.md                         → NUEVO (raíz)
   TECHNICAL_FEASIBILITY.md                     → NUEVO (raíz)
   ONLINE_AUTOMATION_ANALYSIS.md                → NUEVO (raíz)
   PLAN_IMPLEMENTACION_GITHUB.md                → NUEVO (raíz)
   ```
   (`task.py.diff` es solo para que puedas revisar exactamente qué cambió en ese archivo antes de sobrescribirlo — no hace falta aplicarlo, `task.py` ya viene completo y listo.)
5. Sube los cambios:
   ```bash
   git add -A
   git commit -m "Adapt MoneyPrinterTurbo for zero-cost GitHub Actions automation"
   git push
   ```
6. Sigue `README_ADAPTACION.md` para dar de alta los Secrets y probarlo con "Run workflow" antes de dejarlo en piloto automático diario.

### Si prefieres no usar git
Puedes hacer lo mismo desde la web de GitHub: entra en tu fork, usa "Add file → Upload files" para los nuevos, y para `app/services/task.py` / `config.example.toml` entra al archivo → lápiz de editar → pega el contenido nuevo → commit. Más lento pero funciona igual de bien para un cambio de este tamaño.
