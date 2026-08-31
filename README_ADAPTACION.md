# README_ADAPTACION.md
## Fork adaptado de MoneyPrinterTurbo para correr 100% en GitHub Actions, coste 0€

Base: [harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (MIT). Ver `TECHNICAL_FEASIBILITY.md`, `ONLINE_AUTOMATION_ANALYSIS.md` y `PLAN_IMPLEMENTACION_GITHUB.md` en la raíz para el porqué de cada decisión.

## Qué se cambió respecto al original

- **Nuevo:** `app/services/official_publish.py` — publica directamente vía YouTube Data API v3, TikTok Content Posting API e Instagram Graph API. Sin intermediario de pago.
- **Nuevo:** `app/services/github_asset_host.py` — hospeda temporalmente el vídeo como asset de una Release de GitHub, solo para darle a Instagram una URL pública que pueda leer (su API lo exige).
- **Modificado (diff mínimo):** `app/services/task.py` — cuando `official_publish_enabled = true`, usa el publicador oficial en vez de Upload-Post. Con `official_publish_enabled = false` (por defecto) el comportamiento original con Upload-Post queda intacto.
- **Nuevo:** `config.example.toml` — añadida la sección "Official-API Publishing".
- **Nuevo:** `scripts/render_config.py`, `scripts/pick_topic.py`, `scripts/publish_video.py` — pegamento para que todo corra como un job de un solo disparo en Actions.
- **Nuevo:** `.github/workflows/daily_episode.yml` — el cron diario.
- **Nuevo:** `content/topics_queue.txt` — tu cola de temas (edítala).

## Puesta en marcha (una sola vez)

### 1. Crea el repositorio
Sube este contenido a un repo nuevo en tu cuenta de GitHub. **Recomiendo que sea público**: da minutos de Actions ilimitados gratis, y es lo que permite que el truco de hosting temporal para Instagram funcione (los Secrets de GitHub nunca se exponen aunque el repo sea público — solo se hace público el código y los vídeos publicados como Release temporal).

### 2. Da de alta los Secrets
`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Obligatorio | De dónde sale |
|---|---|---|
| `PEXELS_API_KEY` | Sí | https://www.pexels.com/api/ (gratis, al instante) |
| `PIXABAY_API_KEY` | No (recomendado) | https://pixabay.com/api/docs/ (gratis, al instante) |
| `GROQ_API_KEY` | Sí | https://console.groq.com/keys (gratis, al instante — es el LLM que escribe el guion) |
| `YOUTUBE_CLIENT_ID` | Para publicar en YouTube | ver sección "YouTube" abajo |
| `YOUTUBE_CLIENT_SECRET` | Para publicar en YouTube | ídem |
| `YOUTUBE_REFRESH_TOKEN` | Para publicar en YouTube | ídem |
| `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` / `TIKTOK_REFRESH_TOKEN` | Para publicar en TikTok | ver sección "TikTok" |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` / `INSTAGRAM_ACCESS_TOKEN` | Para publicar en Instagram | ver sección "Instagram" |

### 3. Variables no secretas (opcional)
`Settings → Secrets and variables → Actions → pestaña Variables`:
- `OFFICIAL_PUBLISH_PLATFORMS` = `youtube` (o `youtube,tiktok,instagram` cuando tengas los tres listos)
- `YOUTUBE_PRIVACY_STATUS` = `public` | `unlisted` | `private` (útil poner `unlisted` mientras pruebas)

### 4. Tu cola de temas
Edita `content/topics_queue.txt` con tus propios temas, uno por línea. El workflow va consumiendo la lista de arriba a abajo y anota lo ya usado en `content/used_topics.json` (se commitea solo). Añade más líneas cuando se acabe.

---

## Cómo conseguir cada credencial

### YouTube (empieza por aquí — sin auditoría previa)
1. [Google Cloud Console](https://console.cloud.google.com/) → crea un proyecto → habilita **"YouTube Data API v3"**.
2. **Pantalla de consentimiento OAuth** → tipo *External* → añade tu propia cuenta de Google como *test user* (no hace falta publicar la app para uso propio).
3. **Credenciales** → *Create credentials* → *OAuth client ID* → tipo **Desktop app**. Anota `client_id` y `client_secret`.
4. Genera el `refresh_token` **una vez, en tu ordenador** (no en GitHub) con el scope `https://www.googleapis.com/auth/youtube.upload`, por ejemplo con `google-auth-oauthlib`:
   ```python
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_config(
       {"installed": {"client_id": "...", "client_secret": "...",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"}},
       scopes=["https://www.googleapis.com/auth/youtube.upload"],
   )
   creds = flow.run_local_server(port=0)
   print(creds.refresh_token)
   ```
   Ese `refresh_token` no caduca salvo que revoques el acceso — guárdalo como secret y listo.

### TikTok (cuando la app pase la auditoría — inícialo ya, tarda semanas)
1. [developers.tiktok.com](https://developers.tiktok.com/) → crea una app → solicita los scopes `video.publish` y `video.upload`.
2. Completa el flujo OAuth una vez (puedes usar Postman o un script local con tu propia URL de redirect) para obtener el `refresh_token`.
3. Mientras la app no esté auditada, **TikTok fuerza cualquier publicación a privada** — no es un fallo de este código, es una restricción de TikTok explicada en `ONLINE_AUTOMATION_ANALYSIS.md`.

### Instagram (cuando pase la revisión — inícialo ya, tarda 2-4 semanas)
1. [developers.facebook.com](https://developers.facebook.com/) → crea una app tipo *Business*.
2. Añade el producto **Instagram Graph API** → solicita `instagram_business_basic` e `instagram_business_content_publish`.
3. Tu cuenta de Instagram debe ser **Business** (no Creator) y estar vinculada a una Página de Facebook.
4. Genera un token de acceso de larga duración (recomendado: System User token) con esos permisos.
5. Consigue el `instagram_business_account_id` con el Graph API Explorer: `GET /me/accounts` → luego `GET /{page-id}?fields=instagram_business_account`.

---

## Probarlo antes de dejarlo en piloto automático

Pestaña **Actions** del repo → *Daily Episode* → **Run workflow** (lo dispara manualmente, sin esperar al cron). Revisa el log de cada paso: `result.json` (lo que generó `cli.py`) y la respuesta de `publish_video.py` se imprimen ahí mismo.

## Si un paso falla

El job se marca como fallido en la pestaña Actions (puedes activar notificaciones por email en tu perfil de GitHub). `content/used_topics.json` solo se actualiza al final (`if: always()`), así que un fallo antes de ese paso no "quema" el tema — se reintentará el día siguiente. Si falla **después** de commitear el tema mismo pero antes de publicar, tendrás que devolverlo manualmente a la cola si quieres reintentarlo ese mismo tema.

## Limitaciones conocidas de esta primera versión

- **Metraje de stock, no personajes propios** — ver la sección 6 de `ONLINE_AUTOMATION_ANALYSIS.md` para el porqué y cómo migrar más adelante si el canal funciona.
- TikTok/Instagram no publicarán en público hasta pasar sus respectivas revisiones (YouTube sí, desde el primer día).
- Sin reintentos automáticos todavía (el `MAX_RETRIES=3` / `FAILED → continuar` de los puntos 19 y 28 del brief original) — pendiente para una siguiente iteración.
- Cuota de YouTube: 10.000 unidades/día, ~1.600 por subida → techo práctico de ~6 vídeos/día sin pedir ampliación.
