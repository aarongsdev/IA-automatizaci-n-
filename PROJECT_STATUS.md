# Estado del proyecto — El Reino de las Fábulas

Documento de contexto para retomar el trabajo desde cualquier sesión (nube o local). Se actualiza a mano cuando hay cambios grandes. **Nunca contiene valores de secrets/API keys reales** — solo nombres y dónde están guardados.

## Qué es esto

Canal de YouTube **"El Reino de las Fábulas"** (@ElReinoDeFabulasTV): cuentos infantiles episódicos en español, generados y publicados 100% automáticamente vía GitHub Actions, sin coste. Formato "frutinovela" adaptado: personajes recurrentes, relaciones, secretos y giros entre capítulos, en vez de cuentos sueltos.

## Arquitectura actual (pipeline en la nube, `.github/workflows/daily_episode.yml`)

1. **`scripts/decide_next_episode.py`** — un LLM (Groq) hace de showrunner: decide si continuar la serie en curso, cerrarla, empezar otra del reparto precast, o inventar una nueva. Mantiene `content/show_state.json` (biblia de personajes, secretos ocultos, tramas abiertas) como memoria persistente entre episodios. Si falla, cae a `scripts/pick_topic.py` (cola estática de respaldo).
2. **`cli.py`** (MoneyPrinterTurbo) — genera el guion (LLM), la voz (EdgeTTS, una sola voz narradora), busca vídeo de stock por palabra clave por frase (Pexels, `--match-materials-to-script`), y renderiza el vídeo 9:16.
3. **`scripts/overlay_mascot.py`** — superpone la mascota (PNG dibujado a mano) de la serie/personaje del capítulo.
4. **`scripts/burn_hook_text.py`** — quema en el vídeo el texto del gancho inicial y el cliffhanger final (para gente que ve sin sonido).
5. **`scripts/generate_thumbnail.py`** — genera la miniatura (mascota + gancho del guion).
6. **`scripts/publish_video.py`** — publica en YouTube con título/descripción/hashtags optimizados generados a partir del guion (sin llamada extra al LLM).

Cron: martes/jueves/sábado 10 AM hora México. `workflow_dispatch` manual tiene un input `publish` (boolean) para lanzar en modo prueba sin publicar.

## Personajes y series (`content/show_state.json`)

Reparto precast (mascota ya dibujada, `assets/characters/`): Luna (zorrita), Toby (barco de papel), Pipo (elefante), Mar y Leo (hermanos), Teodoro y Alba (rey y niña del pueblo). Cuando el LLM inventa un personaje nuevo (solo si se agota el reparto), escribe un brief visual detallado en texto -- nunca genera ni dibuja nada, eso sigue siendo un paso manual (como con Toby).

**Estado del show: reiniciado a cero el 16 sept 2026** porque nada se había publicado realmente todavía (antes por falta de credenciales, luego por un bug que saltaba el paso de publicar). El primer episodio que se publique de verdad será Luna Capítulo 1.

## Secrets configurados (solo nombres -- valores en GitHub Settings → Secrets and variables → Actions)

- `PEXELS_API_KEY` — banco de vídeo de stock
- `GROQ_API_KEY` — LLM (modelo `openai/gpt-oss-120b` por defecto)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` — publicación en YouTube (cliente OAuth "Web application" llamado "claude web" en Google Cloud Console, proyecto `claude-ia-video`)
- `GITHUB_TOKEN` — automático, lo provee GitHub Actions

**Pendiente de verificar**: el `YOUTUBE_REFRESH_TOKEN` se generó el 4 sept mientras la app de Google seguía en modo "Prueba" (caduca a los 7 días salvo que se publicara la app). Comprobar si sigue vivo o hay que regenerarlo.

## Bugs importantes ya corregidos (por si reaparecen síntomas parecidos)

- `GROQ_BASE_URL`/`GROQ_MODEL_NAME` como cadena vacía rompía el showrunner en silencio (usar `or`, no `os.environ.get(x, default)`)
- `.gitignore` estaba sin el punto inicial (renombrado, ya funciona)
- Vídeo no reproducible en Windows (`0x80004005`) por copiar el codec de audio original -- ahora se fuerza H.264+AAC+yuv420p
- La condición del "modo prueba" (`inputs.publish`) saltaba el paso de publicar también en los runs automáticos del cron -- corregido para mirar `github.event_name`

## Línea nueva en marcha: vídeo generado por IA en local (separado del pipeline en la nube)

El usuario tiene una **RTX 2060 (6GB VRAM)** en su PC. Investigación ya hecha (sin acceso directo a ese PC desde esta sesión en la nube):

- **Wan2GP + Wan 2.2 14B cuantizado (GGUF Q3_K/Q4_K)** en ComfyUI, con el text encoder T5 descargado a RAM del sistema, es la única combinación con evidencia real de funcionar en 6GB VRAM (480p, ~10-15 min/clip corto). Licencia Apache 2.0.
- LTX-Video (~32GB VRAM mínimo) y Wan sin cuantizar (65-80GB) quedan descartados para esta tarjeta.
- Lip-sync (Wav2Lip) necesita vídeo del personaje ya generado -- depende de resolver antes el paso anterior.
- **Pendiente**: el usuario debe ejecutar en su PC `nvidia-smi`, `python --version`, `wmic memorychip get capacity`, `wmic logicaldisk get size,freespace,caption`, `winver` y compartir el resultado (aquí o en una sesión local de Claude Code) para confirmar viabilidad real antes de instalar nada.
- Este prototipo de vídeo local es un desarrollo aparte del pipeline de GitHub Actions -- no se integra hasta que funcione de forma independiente (Fases 1-9 acordadas: auditoría → investigación → elegir opción → instalar → prototipo 1 personaje → Luna+2º personaje → voces distintas → integración → episodio completo).

## Próximos pasos

1. Confirmar si el `YOUTUBE_REFRESH_TOKEN` sigue vivo (o repetir el intercambio OAuth si caducó)
2. Lanzar el primer episodio real (Luna Capítulo 1) cuando el usuario dé el visto bueno
3. Fase 1 del prototipo de vídeo local: auditoría del PC con RTX 2060
