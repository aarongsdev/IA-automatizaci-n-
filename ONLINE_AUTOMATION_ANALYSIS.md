# ONLINE_AUTOMATION_ANALYSIS.md
## ¿Puede Claude hacerlo "desde aquí", cada día, sin que toques nada?

Fecha: 31 agosto 2026 · Complementa a `TECHNICAL_FEASIBILITY.md`

---

## 1. LA PREGUNTA REAL QUE HAY QUE RESOLVER PRIMERO

"Que lo haga yo (Claude) desde aquí" puede significar dos cosas muy distintas, y hay que elegir una antes de construir nada:

**(A) Que la GENERACIÓN pesada (imágenes, vídeo, voz) ocurra en algún sitio online** — tu PC con la RTX 2060 no tiene que estar encendido.
**(B) Que la ORQUESTACIÓN diaria (arrancar el proceso, controlar calidad, publicar) la dispare Claude solo, sin que abras nada** — pero el cómputo pesado puede seguir ocurriendo en tu PC.

Este entorno en la nube donde te estoy hablando ahora **no tiene GPU**. No puedo ejecutar SDXL, Wan ni Kokoro-a-escala aquí dentro. Así que la opción (A) "todo en la nube" **no puede usar tu RTX 2060** — necesita GPU de otro sitio, y eso tiene un coste real, aunque sea pequeño. La opción (B) sí puede lograrse sin coste, pero exige que tu PC esté encendido y accesible en el momento en que toca generar.

---

## 2. CÓMO LO HACEN OTROS CREADORES CON CLAUDE (patrón real, verificado)

He revisado plantillas y casos reales de automatización de shorts con Claude (agosto 2026), incluyendo un workflow público de n8n ["Automate TikTok and Instagram trend videos with Claude, Seedance 2.0 and Blotato"](https://n8n.io/workflows/15203-automate-tiktok-and-instagram-trend-videos-with-claude-seedance-20-and-blotato/). El patrón se repite:

```
Claude (Cowork/API)          → analiza tendencias, decide el concepto,
                                escribe el prompt de vídeo y el caption
        ↓ (webhook)
n8n (cloud, no en tu PC)     → orquesta el flujo
        ↓
API de pago de vídeo         → Seedance 2.0 / Sora 2 (vía AtlasCloud u otro
                                proveedor) genera el vídeo con audio, 720p, 9:16
        ↓
Blotato (servicio de pago)   → publica en TikTok, Instagram, YouTube, etc.
```

**Claude aquí no genera vídeo ni imagen** (no es su función) — genera **ideas, guion y prompts**, y decide. Todo el trabajo pesado (vídeo, voz) lo hace una **API de pago por generación**, y la publicación la hace un **servicio de terceros de pago** (Blotato), no las APIs oficiales llamadas directamente.

**Esto es exactamente el patrón que tu brief original pedía evitar**: depender de APIs de vídeo de pago por uso como método principal. Es rápido de montar y 100% "en la nube", pero el coste por vídeo deja de ser €0 (pasa a depender de tarifas de Seedance/Sora/Blotato, no publicadas de forma transparente, y que se acumulan cada día). Te lo cuento porque es honesto que lo veas: es la vía más popular ahora mismo, pero no es tu vía si el requisito de coste 0€ sigue en pie.

---

## 3. LAS OPCIONES REALES PARA TI (con coste y complejidad honestos)

### Opción 1 — Tu PC como "servidor casero" siempre encendido + disparo remoto (mantiene €0)

Tu RTX 2060 se queda encendida (o se enciende con temporizador) y expone ComfyUI/Ollama/Kokoro como una API local protegida, accesible desde fuera vía **Cloudflare Tunnel** (gratis, sin abrir puertos, sin exponer tu IP — [guía técnica](https://www.sygnal.com/kb/exposing-comfyui-as-an-external-api)). Un disparador en la nube (n8n cloud gratuito, GitHub Actions con cron, o un **scheduled task de Claude**) llama a esa API cada día a las 04:00, tu PC genera todo, sube el vídeo final a almacenamiento en la nube, y otro paso (que sí puede correr aquí, en la nube) publica vía las APIs oficiales.

- **Coste marginal:** €0 de API (solo electricidad, como ya contemplaba el brief).
- **Contrapartida:** el PC tiene que estar encendido y con red estable en el momento programado. Si se apaga o pierde conexión, ese día falla (hay que contemplarlo en el `FAILED → continuar` del punto 28).
- **Seguridad:** ComfyUI no tiene autenticación propia — hay que añadir un proxy con token (Cloudflare Access, o un middleware simple) antes de exponerlo, si no cualquiera en internet podría usarlo.

### Opción 1b — Variante sin túnel: Claude como orquestador con "device binding"

Esta sesión (Cowork) tiene una función nativa para esto: puedo crear una **tarea programada** (`scheduled task`) que se ejecute cada día y que, si tu ordenador está encendido con la app de Claude abierta en ese momento, **se vincule directamente a tu PC** y ejecute comandos ahí (arrancar ComfyUI, generar, renderizar con FFmpeg, etc.) sin necesidad de montar un túnel ni exponer nada a internet. Es la opción más simple de las que mantienen €0, pero tiene la misma condición: tu PC debe estar encendido y la app abierta a esa hora.

- **Coste marginal:** €0.
- **Contrapartida:** misma que la Opción 1 (PC encendido), pero sin trabajo de red/seguridad adicional. Es la que recomendaría probar primero.

### Opción 2 — GPU de alquiler bajo demanda, solo mientras genera (coste bajo pero real)

En vez de una API de "vídeo por IA" de pago por generación (cara, propietaria), se alquila **GPU en bruto** (ej. RunPod) solo los minutos que dura la generación, y ahí se ejecutan los **mismos modelos open-source** (SDXL, Wan, Kokoro) que en tu PC. No necesita que tu ordenador esté encendido nunca.

- **Coste real de referencia (agosto 2026):** RTX 4090 en RunPod ≈ **$0,74/hora**; si un episodio tarda ~20-30 min de GPU (imágenes + algo de vídeo experimental), serían aproximadamente **$0,25-0,40 por episodio** (unos 0,23-0,37 €). Con 1-2 vídeos/día serían entre **7 € y 20 € al mes**, aproximadamente — nada que ver con las tarifas de las APIs de vídeo de pago por generación (Seedance/Sora/Runway), que suelen ser más caras por clip.
- **Ventaja:** verdaderamente "sin intervención" — no depende de que tu PC esté encendido.
- **Contrapartida:** dejas de tener coste €0 estricto; pasa a ser `COST_MODE=HYBRID` con un coste de cómputo pequeño y predecible (no de "API de generación de pago" en el sentido que tu brief quería evitar, sino de alquiler de hardware crudo — la distinción que pedías en el punto 20, COST TRACKING, entre API COST y COMPUTE COST).

### Opción 3 — El patrón popular (Seedance/Sora + ElevenLabs + Blotato)

Lo describo por transparencia, no porque lo recomiende: es la vía más rápida de montar y la que usa la mayoría de tutoriales "hazte rico con IA" que aparecen ahora mismo. Rompe dos cosas de tu brief: coste 0€ (tarifas por generación no publicadas con claridad, se acumulan) y "solo APIs oficiales" (Blotato es un intermediario de pago, no la API nativa). La descarto salvo que me digas explícitamente que prefieres velocidad de puesta en marcha sobre el requisito de coste.

---

## 4. RECOMENDACIÓN

Para cumplir lo que pediste desde el principio (coste 0€, sin depender de APIs de pago por generación), lo lógico es:

1. **Empezar con la Opción 1b** (scheduled task de Claude + device binding a tu PC): cero coste, cero infraestructura nueva, y es literalmente "que lo haga yo desde aquí cada día" tal como lo has pedido — con la única condición de que tu PC esté encendido a la hora programada (algo asumible si lo dejas como un mini-servidor).
2. Si en el futuro quieres independencia total de tu PC (por ejemplo, viajas y lo apagas), la **Opción 2** (GPU de alquiler bajo demanda) es el siguiente escalón, con un coste bajo y controlado que declararíamos honestamente en el dashboard como `COMPUTE COST`, nunca como "€0 total", tal como ya pedía el punto 20 de tu brief.
3. Evitaría la Opción 3 salvo que cambies de prioridad.

---

## 5. ¿EXISTE ALGUNA FORMA 100% "EN LA NUBE" QUE SEA REALMENTE 0€? — Verificado

Pregunta directa, respuesta directa tras revisar las condiciones de servicio reales (agosto 2026) de las plataformas que sí ofrecen GPU gratis: **no, no existe una vía 100% online, gratuita y apta para producción diaria desatendida.** No es una opinión, es lo que dicen sus propias condiciones:

- **Google Colab (gratis):** su propia documentación dice literalmente que el uso automatizado sin un humano interactuando **no está permitido**: prohíbe "ejecutar workers de computación distribuida", conectarse por SSH/escritorio remoto, y usarlo para "file hosting, media serving u otros servicios no relacionados con computación interactiva". Además, **no garantiza recursos** ("no proporciona recursos garantizados ni ilimitados") y los límites de GPU varían sin previo aviso. Un pipeline diario desatendido viola sus condiciones directamente.
- **Kaggle (gratis):** da 30h/semana de GPU T4/P100, en teoría suficiente en horas — pero exige parar las sesiones manualmente, penaliza el "bot abuse", y sus sesiones están pensadas para trabajo interactivo, no como servidor de producción 24/7. Automatizarlo para un negocio de contenido diario cae en zona gris de sus términos.
- **GitHub Actions:** su capa gratuita **no incluye GPU en absoluto** (solo runners de CPU); los runners con GPU son de pago.
- **No existe ningún proveedor cloud con un tier "GPU siempre gratis"** pensado para carga de producción — todo lo que ofrecen otros (Oracle, GCP, AWS, IBM) en "always free" es CPU/almacenamiento básico, nunca GPU.

En resumen: **cualquier oferta "gratis" de GPU en la nube es, por diseño, incompatible con "todos los días, sin intervención, para un producto que vas a monetizar".** Usarla así puede acabar en cuenta suspendida en cualquier momento — la peor base posible para algo que debe funcionar "durante días sin intervención humana" como pide tu brief.

Esto deja solo dos caminos honestos, no tres:

| | Coste real | ¿Depende de tu PC? | ¿Cumple ToS/fiable para producción? |
|---|---|---|---|
| **Tu PC como servidor casero** (Opción 1/1b) | 0€ de API (solo luz) | Sí, debe estar encendido a la hora programada | Sí, es tu propio hardware |
| **GPU de alquiler bajo demanda** (Opción 2, ej. RunPod) | ~7-20€/mes | No | Sí, es un servicio comercial pensado para esto |

No hay una tercera vía gratuita y fiable a la vez. Si el requisito de 0€ es innegociable, la única opción real es que tu PC actúe de servidor (encendido a la hora programada). Si prefieres no depender nunca de tu PC, hay que aceptar el coste bajo pero real de la Opción 2 y declararlo en el dashboard como `COMPUTE COST` (no como €0 total, tal como ya pedía el punto 20 de tu brief).

---

## 6. ¿Y DESDE GITHUB? — Sí, y mejora las dos opciones reales

GitHub no resuelve el problema de fondo (**GitHub no da GPU gratis**, igual que Colab/Kaggle no la dan de forma legítima), pero **GitHub Actions sí aporta algo que Colab y Kaggle no tienen: es un programador de tareas gratuito y explícitamente diseñado para ejecución automática/desatendida** (`on: schedule`, sintaxis cron, es su caso de uso principal, no una zona gris de sus condiciones). Esto mejora las dos opciones de la sección 5:

### 6.1 GitHub como "cerebro" gratuito (sin GPU) — mejora la Opción 2

Los runners de GitHub-hosted (en la nube de GitHub) son **gratis: 2.000 min/mes en repos privados, minutos ilimitados en repos públicos** — pero **no tienen GPU**, solo CPU. Sirven perfectamente para todo lo que NO necesita GPU: el LLM si se usa un modelo pequeño en CPU (Phi-4-mini), TTS (Kokoro/Piper funcionan bien en CPU), STT (faster-whisper), el render final con FFmpeg, la memoria narrativa persistente (guardándola como JSON/SQLite en el propio repo, haciendo commit tras cada episodio), el control de calidad y la publicación vía APIs oficiales. Solo para el paso de generación de imágenes (el único realmente pesado en GPU) el workflow de GitHub Actions haría una llamada HTTP a un endpoint de GPU de alquiler (ej. RunPod serverless), que se enciende solo esos 2-5 minutos y se apaga. Resultado: **ya no hace falta pagar ni auto-hospedar n8n** — GitHub Actions gratis sustituye esa capa de orquestación, y el único coste real sigue siendo el de la Opción 2 (~7-20€/mes de GPU), ahora más ajustado porque solo se paga la generación de imágenes, no todo el pipeline.

### 6.2 GitHub como disparador de TU PC — mejora la Opción 1 (recomendado si tu PC puede quedarse encendido)

Existe el **"self-hosted runner"**: un pequeño programa que instalas en tu propio PC con la RTX 2060, se registra en tu repositorio de GitHub y **se conecta él mismo hacia fuera** (conexión saliente) para recoger el trabajo — **no necesitas abrir ningún puerto ni montar un túnel** (a diferencia de exponer ComfyUI con Cloudflare Tunnel, que sí requiere esa capa de seguridad adicional). GitHub programa la tarea cada día por cron, tu PC la recoge, ejecuta todo el pipeline completo con tu GPU (SDXL, Kokoro, FFmpeg...), y al final el mismo workflow publica con las APIs oficiales. Es gratis siempre — **"el uso de self-hosted runners es gratuito", con o sin repo público, no consume minutos facturables** (nota: GitHub anunció y luego pospuso cobrar por esto en 2026 — no es un riesgo hoy, pero conviene vigilarlo).

**Esta es, en la práctica, la mejor versión de la Opción 1**: mismo coste (0€, salvo luz), misma condición (tu PC debe estar encendido a la hora programada), pero con una infraestructura de disparo más simple, más segura (sin exponer nada a internet) y más madura que un túnel o que depender de que tu ordenador esté vinculado a una sesión de Claude en ese momento exacto.

---

## 7. ¿EXISTE YA UN REPOSITORIO EN GITHUB QUE HAGA ESTO? — Búsqueda real

He buscado en GitHub proyectos existentes que puedan reutilizarse. Resultado honesto: **ninguno hace exactamente lo que pide tu brief (personajes IA propios y consistentes, universo persistente, generación local de imágenes) funcionando 100% dentro de GitHub Actions gratis** — y no es que falte buscar, es que esa combinación es físicamente imposible sin GPU en algún sitio, y GitHub Actions gratis no tiene GPU (la misma limitación de siempre). Aun así, hay proyectos maduros de los que sí se puede partir, con matices importantes:

### MoneyPrinterTurbo ([harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)) — el más serio con diferencia
- **110.000+ estrellas, 16.700+ forks, licencia MIT, mantenimiento activo.** Con muchísima diferencia el proyecto open-source más maduro de esta categoría.
- Genera guion con LLM (soporta **Ollama local gratis**, o proveedores de pago), voz con **Edge TTS (gratis)**, subtítulos con Edge TTS o faster-whisper local, y monta el vídeo con **metraje de stock de Pexels/Pixabay/Coverr** (gratis, con licencia de uso).
- Tiene **API REST propia** (`python main.py`, documentación en `/docs`), pensada para uso headless/automatizado — requisitos mínimos solo **4 núcleos de CPU y 4GB de RAM**, GPU opcional. Esto **sí cabría dentro de un runner gratuito de GitHub Actions** sin problema de recursos.
- **Pero (importante):** su modo "gratis por defecto" usa **metraje de stock genérico, no genera tus propios personajes consistentes** (Strawby, Banan, Mango... como pedía tu brief en el punto 8-12). Tiene una opción de "vídeo generado por IA" pero usa **WaveSpeed AI y Volcano Engine Seedance — APIs de pago por generación**, justo lo que tu brief quería evitar. Y su publicación automática depende de un servicio de terceros de pago ("Upload-Post"), no de las APIs oficiales directamente — como Blotato, otro intermediario más.

**Traducción honesta:** si aceptas cambiar "mi propio universo de personajes con imágenes generadas por IA" por "montaje con metraje de stock + narración con IA", MoneyPrinterTurbo en su modo gratuito **sí podría ejecutarse entero dentro de GitHub Actions, sin PC, sin coste, hoy mismo** — sería cuestión de adaptarlo (conectarlo a un runner con cron, y cablear la publicación a las APIs oficiales en vez de a Upload-Post, para respetar el punto 22 de tu brief). Si quieres mantener el universo de personajes propios, ese cambio de stock-footage no sirve, y seguimos necesitando GPU en algún sitio (tu PC o alquilada) para la parte de imágenes — ningún repositorio existente se salta esa barrera física.

### Otros proyectos revisados (menos relevantes para tu caso)
- [Sba-Stuff/AI-Local-Video-Generator](https://github.com/Sba-Stuff/AI-Local-Video-Generator) — LLM local (LM Studio) + metraje de stock Pexels/Pixabay, MIT, pero apenas iniciado (0 estrellas) y pensado para ejecutarse con un servicio local activo (LM Studio), no encaja bien en un runner efímero de GitHub Actions.
- [prakashdk/video-creator](https://github.com/prakashdk/video-creator) — sí genera imágenes con Stable Diffusion local (más parecido a tu visión), pero es un proyecto pequeño (pocas estrellas, actividad limitada), sin mención de consistencia de personajes entre vídeos, y como usa SD necesitaría GPU igualmente.
- [darkzOGx/youtube-automation-agent](https://github.com/darkzOGx/youtube-automation-agent) — agentes de IA con Gemini gratis, pero centrado en gestión de canal, no en generación de imágenes propias.

Ninguno de estos resuelve el "GPU gratis en la nube" porque, como confirmamos en la sección 5, **eso no existe**.

---

## 8. LO QUE NECESITO DE TI PARA CONTINUAR

Antes de tocar código, necesito que confirmes la dirección (esto cambia el diseño de los `Providers` del punto 24 del brief — `ImageProvider`/`VideoProvider`/`VoiceProvider` locales vs. remotos):

- ¿Tu PC con la RTX 2060 puede quedarse encendido y conectado a diario a la hora en que quieres que se genere el contenido (por ejemplo, de madrugada)? → si sí, vamos con **GitHub self-hosted runner en tu PC** (6.2): 0€ real, sin exponer nada a internet.
- ¿O prefieres no depender nunca de tu PC? → vamos con **GitHub Actions (gratis) + GPU de alquiler solo para las imágenes** (6.1): ~7-20€/mes, sin tocar tu ordenador.

Con tu respuesta, ajusto el plan de implementación y seguimos con la Fase 1.5 (benchmark real).
