# PLAN_IMPLEMENTACION_GITHUB.md
## Decisión tomada y plan de puesta en marcha (Fase 2 revisada)

Fecha: 31 agosto 2026

---

## DECISIÓN REGISTRADA

Tras el análisis de `TECHNICAL_FEASIBILITY.md` y `ONLINE_AUTOMATION_ANALYSIS.md`, se decide:

> **Adaptar [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (110k★, MIT) para que se ejecute 100% dentro de GitHub Actions (runners gratuitos en la nube), sin usar la RTX 2060 ni ningún PC.**

Esto implica **renunciar, por ahora, al universo de personajes IA propios y consistentes** (Fruit City, puntos 8-12 del brief original) a cambio de **coste 0€ real y cero dependencia de hardware propio**. El contenido se monta con metraje de stock (Pexels/Pixabay/Coverr) + guion y voz generados por IA. Si más adelante el canal funciona, se puede migrar a personajes propios añadiendo GPU (tu PC o alquilada) sin rehacer el resto del sistema — es exactamente lo que resuelve el patrón de `Providers` intercambiables del punto 24 del brief.

**Piezas que se retiran de la versión por defecto de MoneyPrinterTurbo** (por no cumplir tus requisitos):
- Generación de vídeo por IA con WaveSpeed/Seedance → **API de pago, se desactiva**.
- Publicación vía "Upload-Post" → **servicio de terceros de pago, se sustituye por llamadas directas a las APIs oficiales de YouTube/TikTok/Instagram**, como pedía el punto 22 del brief.

---

## QUÉ VOY A PREPARAR YO (en este entorno, sin esperar nada tuyo)

1. Clonar MoneyPrinterTurbo y revisar su configuración real (`config.toml`) para dejar solo las opciones gratuitas activas: Ollama o un LLM de free-tier, Edge TTS, Pexels/Pixabay, faster-whisper.
2. Escribir un módulo `official_publishers/` nuevo (Python) que suba directamente vía **YouTube Data API v3**, **TikTok Content Posting API** y **Instagram Graph API** — sin pasar por Upload-Post.
3. Escribir el workflow de **GitHub Actions** (`.github/workflows/daily_episode.yml`) con `on: schedule` (cron diario), que instale dependencias, arranque el LLM elegido, genere el episodio, haga control de calidad básico y publique.
4. Documentar exactamente qué secrets hay que dar de alta en el repo (`Settings → Secrets and variables → Actions`).

Todo esto lo puedo dejar listo como archivos que te entrego, aunque **el repositorio final en GitHub lo tienes que crear tú** (no tengo acceso de escritura a tu cuenta de GitHub desde aquí) — te doy el paquete ya montado para que solo tengas que subirlo.

---

## QUÉ NECESITO DE TI (cuentas/credenciales — puedes irlas preparando en paralelo)

| Servicio | Para qué | Coste | Tiempo estimado de alta |
|---|---|---|---|
| Cuenta de GitHub (si no la tienes) | Alojar el repo y ejecutar Actions | 0€ | 5 min |
| Pexels API key | Metraje de stock | 0€ | 2 min |
| Pixabay API key | Metraje de stock | 0€ | 2 min |
| Cuenta LLM: **elige una** → (a) ninguna, uso Ollama dentro del propio runner de Actions, o (b) API key de un proveedor con free-tier (ej. Gemini) | Guion/narración | 0€ en ambos casos | 5 min si (b) |
| Google Cloud Console → YouTube Data API v3 + OAuth | Publicar en YouTube | 0€ | 15-20 min |
| TikTok Developer App → Content Posting API | Publicar en TikTok | 0€, pero **auditoría de semanas** antes de poder publicar en público | Iniciar cuanto antes |
| Meta for Developers → Instagram Graph API (cuenta Business, no Creator) | Publicar en Instagram | 0€, pero **revisión de 2-4 semanas por permiso** | Iniciar cuanto antes |

**Recomendación de orden:** empezar publicando solo en **YouTube** (su API no exige auditoría previa, solo cuota — hasta ~6 subidas/día sin pedir aumento), y lanzar en paralelo las solicitudes de TikTok e Instagram, que sí tardan semanas, para añadirlas en cuanto se aprueben. Así el canal puede arrancar ya en vez de esperar a las tres plataformas a la vez.

---

## SIGUIENTE PASO INMEDIATO

Voy a preparar ya el paquete de código (repo adaptado + workflow de GitHub Actions + módulo de publicación oficial) para que lo tengas listo para subir. Antes de escribir el código de publicación necesito confirmar una cosa práctica: **¿empezamos solo con YouTube y añadimos TikTok/Instagram cuando pasen la auditoría, o prefieres que deje ya el código de las tres preparado (aunque TikTok/Instagram no puedan publicar en público hasta que se aprueben)?**
