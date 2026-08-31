# TECHNICAL_FEASIBILITY.md
## Fábrica Autónoma de Historias IA a Coste €0 por Vídeo — Estudio Técnico (Fase 1)

Fecha: 31 agosto 2026
Hardware objetivo: NVIDIA RTX 2060 6GB · Intel i5-10400 · RAM por determinar automáticamente

---

## 0. LIMITACIÓN IMPORTANTE DE ESTE INFORME — LEER PRIMERO

Este análisis se ha elaborado desde un entorno de trabajo en la nube **sin GPU NVIDIA física**, por lo que **no he podido ejecutar el BENCHMARK REAL (punto 32 del brief) sobre tu RTX 2060 real**. Lo que sí he hecho es una revisión exhaustiva de documentación oficial, foros técnicos y reportes de la comunidad (agosto 2026) para cada componente candidato, contrastando VRAM, licencia, velocidad y compatibilidad.

Esto significa dos cosas:

1. Las cifras de VRAM/tiempo de este documento son **estimaciones de la comunidad**, no medidas en tu máquina. Son la mejor base disponible para decidir arquitectura, pero **no sustituyen el benchmark real**.
2. Como Fase 1 entrego también el **script de benchmark** (`benchmark_suite/`, descrito en el punto 9) para que lo ejecutes tú en tu equipo. Con esos resultados reales confirmamos o ajustamos la arquitectura antes de construir nada de Fase 3 en adelante — tal como pide el punto 33 del brief ("no avanzar sin benchmark real").

No he escrito ninguna línea de código de producción del pipeline. Este documento es únicamente el estudio técnico solicitado.

---

## 1. COMPARATIVA DE TECNOLOGÍAS

### 1.1 Texto / Guion (LLM local)

| Modelo | VRAM (6GB, cuantizado) | Licencia | Uso comercial | Calidad narrativa | Velocidad |
|---|---|---|---|---|---|
| **Qwen2.5-7B-Instruct** (GGUF Q4_K_M) | ~5–6 GB (ajustado, sin margen) | Apache 2.0 | ✅ Sí | Alta, buen multilingüe (ES incluido) | Media, 15–25 tok/s en 2060 |
| **Mistral-7B-Instruct** (GGUF Q3_K_M/Q4_K_S) | ~5–6 GB (justo) | Apache 2.0 | ✅ Sí | Alta para escritura creativa/instrucciones | Media |
| **Phi-4-mini (3.8B)** | ~2.5–3 GB (holgado) | MIT | ✅ Sí | Buena para su tamaño, más simple | Rápida, 25–35 tok/s |
| Llama 3.x 8B | ~5–6 GB | Meta Llama Community License | ⚠️ Comercial permitido pero con cláusulas de uso (marca "Llama", límite 700M MAU) | Alta | Media |

**Nota:** en 6GB reales (sin sistema operativo/otros procesos consumiendo VRAM) los modelos 7B en Q4 quedan **muy ajustados**; cualquier proceso simultáneo (navegador, ComfyUI en segundo plano) puede provocar OOM. Se recomienda offload parcial de capas a CPU vía llama.cpp/Ollama como colchón de seguridad.

### 1.2 Imagen (generación de personajes/escenas)

| Modelo | VRAM en 6GB | Licencia | Uso comercial | Calidad | Velocidad (ComfyUI, 2060) |
|---|---|---|---|---|---|
| **SDXL 1.0 (base)** | Ajustado con `--medvram`/offload | CreativeML Open RAIL++-M | ✅ Sí | Alta, gran ecosistema LoRA/ControlNet | ~50–60s/imagen (1024×896, ComfyUI); **7–8 min en A1111** (evitar A1111) |
| **SDXL Turbo/Lightning** (destilado, pocos pasos) | Igual que SDXL, menos pasos | RAIL++-M (Turbo: licencia más restrictiva, revisar) | ⚠️ Verificar por variante | Algo menor, mucho más rápido | Segundos por imagen |
| **Flux.1 [schnell]** (GGUF Q4-Q8) | ~6–8 GB con cuantización agresiva | Apache 2.0 | ✅ Sí | Muy alta, mejor coherencia que SDXL en algunos casos | Rápido (1–4 pasos), 10–20s/imagen aprox. |
| Flux.1 [dev] | ~6–8 GB (GGUF Q4) | **Non-Commercial License** | ❌ NO permitido en modo €0/monetizado | Muy alta | ~15–25s/imagen |

**Consistencia de personaje:** el entrenamiento de LoRA por personaje en SDXL requiere típicamente **8GB+ de VRAM** de forma cómoda (confirmado en foros de kohya_ss); en 6GB es factible solo con compromisos severos (batch 1, resolución baja, gradient checkpointing, muy lento). **No se recomienda como método principal.** Alternativa viable en 6GB: **IP-Adapter / referencia de imagen + seed fijo + prompt de personaje detallado** (el `visual_seed` del esquema de personaje del punto 10 del brief), reforzado con ControlNet cuando hага falta pose. LoRA por personaje queda como mejora opcional de fondo (proceso overnight, no bloqueante).

### 1.3 Vídeo IA local (imagen-a-vídeo / texto-a-vídeo)

| Modelo | VRAM real | Resolución/duración | Tiempo por clip | Licencia |
|---|---|---|---|---|
| **Wan 2.1 T2V-1.3B** (GGUF Q4) | ~4–6 GB | 480p, 3–5s | Varios minutos | Apache 2.0 |
| **Wan 2.2 TI2V-5B** (FP8) | ~8–10 GB (no cabe cómodo en 6GB) | 720p, 5s | Minutos | Apache 2.0 |
| **Wan 2.2 14B** (GGUF Q4 + offload T5 a CPU) | ~6–9 GB (límite/excede) | 480p, 3–5s | **10–15+ min por clip** | Apache 2.0 |
| **LTX-2 distillado** | 6–8GB con encoders cuantizados | Variable, menor fidelidad | Más rápido que Wan pero con pérdida de calidad | Revisar (histórico: licencia OpenRAIL-M) |

**Conclusión clave:** ningún modelo de vídeo local actual corre **cómodamente** en 6GB reales; el candidato más viable (Wan 2.1 1.3B) queda en el límite y con tiempos de varios minutos por clip de 3-5 segundos. Un short de 45-60s con 10-15 escenas tardaría **entre 2 y 4+ horas solo en generar vídeo**, incompatible con producción diaria desatendida fiable. Se confirma la hipótesis del brief: **la vía de vídeo IA completo no es la arquitectura principal para este hardware.**

### 1.4 Voz (TTS local)

| Motor | Recursos | Licencia | Calidad | Español | Velocidad |
|---|---|---|---|---|---|
| **Kokoro TTS** (82M) | ~2–3 GB GPU o CPU | Apache 2.0 | Muy buena, natural, rivaliza con modelos mayores | Sí (parte de sus ~54 voces/8 idiomas; validar cobertura ES específica) | RTF ≈0.03 (genera 30s de audio en 1s) — muy rápido |
| **Piper** | <1 GB, CPU-first | ⚠️ **GPL-3.0** en el fork activo actual (OHF-Voice/piper1-gpl); el repo original MIT quedó archivado en oct-2025 | Correcta, no top-tier | Sí, voces ES dedicadas | Rápido, ligero |

**Nota de licencia importante:** el Piper "clásico" MIT está descontinuado; el fork mantenido usa GPL-3.0. Para uso interno (no redistribuir el binario) esto no bloquea el modo €0, pero **hay que fijar explícitamente qué repo/versión se usa** y documentarlo, porque copiar/redistribuir binarios GPL con el producto sí tendría implicaciones. Recomendación: **Kokoro como motor principal** (Apache 2.0, sin ambigüedad), **Piper como fallback** documentando su licencia.

### 1.5 STT (subtítulos / verificación)

| Motor | VRAM | Licencia | Notas |
|---|---|---|---|
| **faster-whisper** (CTranslate2, modelo small/base) | <1–2 GB | MIT | Hasta 4× más rápido que Whisper original; recomendado |
| whisper.cpp | CPU, mínimo | MIT | Alternativa sin GPU si hay contención de VRAM |

### 1.6 Render

| Herramienta | Licencia | Notas |
|---|---|---|
| **FFmpeg** | LGPL/GPL según build (x264 es GPL) | Uso interno sin redistribuir el binario modificado → sin conflicto para monetizar el *contenido* generado. Documentar el build usado. |

### 1.7 Orquestación

| Herramienta | Licencia | Notas |
|---|---|---|
| **n8n** (self-hosted) | Sustainable Use License | Gratis para uso interno/personal (no comercializar n8n como servicio a terceros). Encaja exactamente en este caso de uso. |

### 1.8 Música / SFX

No existe una única "librería oficial €0"; se debe curar una `music_library/` combinando fuentes con licencia verificada por pista (Pixabay Music, YouTube Audio Library, CC-BY con atribución cuando aplique). Cada asset debe registrar: fuente, licencia, si requiere atribución y si permite monetización en la plataforma de destino (las políticas de YouTube/TikTok respecto a música de terceros cambian con frecuencia y deben revisarse por pista, no asumirse).

---

## 2. COMPATIBILIDAD CON RTX 2060 6GB

```
HARDWARE COMPATIBILITY
GPU: RTX 2060
VRAM: 6 GB
CPU: Intel i5-10400 (6C/12T)
RAM: [A DETERMINAR AUTOMÁTICAMENTE por el instalador — Fase 2]

Text generation (LLM 7B Q4):        SUPPORTED (ajustado, sin margen de seguridad)
Text generation (LLM 3-4B):         SUPPORTED (holgado, recomendado como base segura)
Image generation (SDXL, ComfyUI):   SUPPORTED (con --medvram / offload, evitar A1111)
Image generation (Flux schnell):    SUPPORTED (GGUF cuantizado)
LoRA training por personaje:        LIMITADO / NO RECOMENDADO (mínimo cómodo: 8GB)
Local TTS (Kokoro/Piper):           SUPPORTED (bajo requerimiento, CPU-friendly)
Whisper STT (faster-whisper):       SUPPORTED
Local video generation (Wan/LTX):   LIMITED — solo variantes pequeñas (Wan 1.3B),
                                     tiempos de 10-15+ min/clip, no viable como
                                     método principal para producción diaria
FFmpeg render 1080x1920:            SUPPORTED (CPU x264, sin cuello de botella de GPU)

Recommended architecture: IMAGE + 2.5D ANIMATION (Opción A del brief)
```

RAM: la documentación de los propios modelos de vídeo (Wan/LTX) recomienda **24–32 GB de RAM** para poder hacer *offload* de componentes a CPU cuando la VRAM no alcanza. Si tu máquina tiene 16GB o menos, esto reduce aún más la viabilidad de cualquier variante de vídeo IA local y refuerza la recomendación de Opción A. **El instalador (Fase 2) debe detectar la RAM real antes de confirmar nada.**

---

## 3. ARQUITECTURA RECOMENDADA

```
STORY ENGINE (memoria narrativa persistente por universo)
        ↓
LLM LOCAL (Qwen2.5-7B-Q4 / Phi-4-mini como base segura)
        ↓
GUION JSON (escenas, diálogos, dirección de cámara)
        ↓
CHARACTER ENGINE (visual_seed + referencia + IP-Adapter, sin LoRA por defecto)
        ↓
SCENE ENGINE
    → SDXL / Flux schnell (ComfyUI) → imágenes de fondo/personaje/foreground
        ↓
ANIMATION ENGINE (2.5D, sin GPU pesada)
    → zoom, pan, parallax, rotación ligera, transiciones, partículas (Python/FFmpeg)
        ↓
TTS LOCAL (Kokoro primario / Piper fallback) — voz persistente por personaje
        ↓
WHISPER (faster-whisper) → verificación + timestamps → SRT/ASS
        ↓
MUSIC/SFX (librería curada con licencia registrada)
        ↓
FFmpeg (compositor final, 1080x1920 9:16, con upscale si se generó a menor resolución)
        ↓
QUALITY CONTROL (checks automáticos + hasta 3 reintentos)
        ↓
SCHEDULER (n8n) → PUBLISH (APIs oficiales YouTube/TikTok/Instagram)
        ↓
ANALYTICS → NEXT EPISODE
```

**Vídeo IA local (Wan 2.1 1.3B)** queda como **Opción B experimental**: se puede activar por escena puntual (p. ej. un "hero shot" de apertura) cuando `COST_MODE=HYBRID` y hay tiempo de sobra, nunca como ruta obligatoria del pipeline diario en modo `ZERO`.

---

## 4. MOTIVO DE ELECCIÓN

1. **VRAM real de 6GB no permite vídeo IA completo con fiabilidad diaria.** Las cifras de la comunidad sitúan cualquier variante utilizable en el límite de la memoria disponible (Wan 1.3B) o directamente por encima (5B/14B), y los tiempos (10-15+ min por clip de 3-5s) hacen inviable producir shorts completos de forma desatendida y repetible cada día.
2. **La generación de imágenes SÍ es sólida en 6GB** vía SDXL/Flux schnell en ComfyUI (no Automatic1111, que es 7-8× más lento en las pruebas comunitarias revisadas).
3. **La animación 2.5D (Ken Burns, parallax, zoom) es prácticamente gratis en cómputo** (CPU/FFmpeg/Python), no compite por VRAM con el LLM ni con la generación de imágenes, y permite paralelizar: mientras se anima la escena N, la GPU puede estar generando la imagen N+1.
4. **Consistencia de personaje sin LoRA** (referencia + seed + prompt estructurado) es más lenta de mejorar iterativamente pero no requiere el margen de VRAM que sí exige el entrenamiento de LoRA, que en 6GB es marginal.
5. **TTS y STT locales son la parte más sólida y barata** de todo el pipeline (Kokoro y faster-whisper apenas usan recursos), así que no son un cuello de botella.
6. Esta arquitectura dedica el recurso más escaso (VRAM) a lo que más impacta la calidad percibida (imágenes de personajes consistentes) en vez de a vídeo generado con IA de calidad dudosa a este nivel de hardware — alineado con el punto 34 del brief ("no producir vídeo IA de mala calidad, usar 2.5D").

---

## 5. LICENCIAS (resumen para consulta rápida)

| Componente | Licencia | Uso comercial/monetización | Acción requerida |
|---|---|---|---|
| Qwen2.5-7B-Instruct | Apache 2.0 | ✅ | Ninguna |
| Mistral-7B-Instruct | Apache 2.0 | ✅ | Ninguna |
| Phi-4-mini | MIT | ✅ | Ninguna |
| Llama 3.x | Meta Community License | ⚠️ Con cláusulas (marca, 700M MAU) | Evitar mencionar "Llama" en marketing si se usa |
| SDXL 1.0 | CreativeML Open RAIL++-M | ✅ | Revisar cláusulas de uso responsable del RAIL |
| Flux.1 schnell | Apache 2.0 | ✅ | Ninguna |
| Flux.1 dev | Non-Commercial | ❌ | **No usar en modo monetizado** |
| Wan 2.1/2.2 (todas variantes) | Apache 2.0 | ✅ | Ninguna (aun así, uso solo experimental por rendimiento) |
| Kokoro TTS | Apache 2.0 | ✅ | Ninguna |
| Piper (fork actual) | GPL-3.0 | ⚠️ Uso interno sin problema; redistribuir binario sí implica GPL | Documentar versión/repo exacto usado |
| faster-whisper / whisper.cpp | MIT | ✅ | Ninguna |
| FFmpeg (build con x264) | LGPL/GPL mixto | ✅ para uso interno | No redistribuir el binario de FFmpeg modificado como parte de un producto vendido |
| n8n | Sustainable Use License | ✅ para automatización interna propia | No ofrecer n8n como servicio a terceros |
| Música/SFX | Variable por pista | Depende | **Registrar licencia por asset**, no asumir "libre" globalmente |

---

## 6. DEPENDENCIAS

- **Runtime IA:** Python 3.11+, PyTorch con CUDA 12.x, `llama-cpp-python` u Ollama, ComfyUI (+ custom nodes: IP-Adapter, ControlNet), `diffusers` como alternativa/soporte.
- **Audio:** Kokoro (paquete pip + modelo ONNX/PyTorch), Piper (binario + voces ES), faster-whisper (CTranslate2).
- **Vídeo/Render:** FFmpeg (build reciente con soporte NVENC si se quiere acelerar codificación), Pillow/OpenCV/MoviePy o script propio para animación 2.5D.
- **Orquestación:** n8n (Docker recomendado), base de datos (SQLite para empezar, Postgres si crece — punto 11 del brief), Redis opcional para colas.
- **Publicación:** SDKs/HTTP oficiales de YouTube Data API v3, TikTok Content Posting API, Instagram Graph API (Meta), gestión OAuth (tokens de refresco).
- **Infra:** CUDA Toolkit + drivers NVIDIA actualizados, `nvidia-smi` para monitorización de VRAM en tiempo real (necesario para el motor de fallback automático del punto 23).

---

## 7. ESPACIO NECESARIO (estimado)

| Elemento | Tamaño aprox. |
|---|---|
| LLM (GGUF Q4, 7B) | 4–5 GB |
| SDXL base (fp16) | ~6.5 GB (o ~3.5-4GB en fp8/variantes optimizadas) |
| Flux schnell (GGUF Q4-Q8) | 6–12 GB según cuantización |
| Wan 2.1 1.3B (GGUF Q4, experimental) | ~2–3 GB |
| Kokoro | ~350 MB |
| faster-whisper (small) | ~500 MB–1.5 GB |
| ComfyUI + custom nodes + entorno Python | 5–10 GB |
| Librería música/SFX curada (inicial) | 5–20 GB (crece con el tiempo) |
| Caché/assets por episodio (antes de limpieza) | 200–500 MB/episodio |
| **Total inicial recomendado (modelos + entorno)** | **~40–60 GB** |
| **Espacio libre recomendado en disco (con margen para meses de episodios)** | **150+ GB** (SSD recomendado) |

---

## 8. TIEMPO ESTIMADO DE GENERACIÓN (por episodio, ~45-60s, 10-15 escenas)

| Etapa | Tiempo estimado (arquitectura recomendada: imagen + 2.5D) |
|---|---|
| LLM: idea + guion + escenas | 30–90 s |
| Generación de imágenes (SDXL, ComfyUI, ~50-60s/img) | 8–15 min |
| Generación de imágenes (alternativa Flux schnell, más rápido) | 3–6 min |
| Animación 2.5D (parallax/zoom, CPU) | 1–3 min |
| TTS (Kokoro, RTF ~0.03) | <15 s |
| STT/verificación (faster-whisper) | <30 s |
| Subtítulos (generación SRT/ASS) | segundos |
| Música/SFX (selección de librería) | segundos |
| Render final FFmpeg (1080x1920) | 1–3 min |
| Control de calidad | <1 min |
| **Total estimado por episodio** | **≈ 15–30 minutos** (viable de sobra para producción diaria nocturna vía n8n) |

**Si se activa Opción B (Wan 1.3B) para 1-2 escenas "hero":** añadir **10–15+ minutos por clip adicional** — usar con moderación y solo si el benchmark real confirma que el tiempo total sigue siendo razonable.

---

## 9. RIESGOS TÉCNICOS

1. **VRAM al límite en 6GB reales.** Los 5-6GB "teóricos" de un modelo Q4 no dejan margen si Windows/el sistema ya reserva 0.5-1GB de VRAM para el escritorio. Mitigación: usar Linux o modo bajo consumo gráfico, cerrar todo lo demás, o forzar offload parcial a CPU.
2. **A1111 es ~8× más lento que ComfyUI en 2060** según reportes comunitarios — decisión de UI/backend no es trivial, impacta directamente el tiempo total.
3. **Consistencia de personaje sin LoRA es más frágil**: puede haber deriva visual entre escenas/episodios; requiere invertir en buenos prompts estructurados, referencia de imagen e IP-Adapter, y validación visual automática (parte del QC).
4. **Licencia de Piper cambió de MIT a GPL-3.0** en el fork mantenido — riesgo de usar por defecto una versión antigua/no mantenida sin darse cuenta. Mitigación: fijar versión exacta y documentarla.
5. **Auditoría de TikTok Content Posting API**: hasta que la app pase la auditoría de Meta/TikTok, **cualquier publicación queda forzada a modo privado** — el pipeline de autopilot no podrá publicar público en TikTok hasta completar ese proceso, cuyo tiempo de revisión no está garantizado por TikTok. Esto es una dependencia externa fuera de nuestro control que **bloquea la Fase 14** hasta resolverse.
6. **Instagram Graph API exige cuenta Business** (no Creator) y revisión de permisos de 2-4 semanas por cada permiso — mismo tipo de riesgo de bloqueo externo, afecta a Fase 15.
7. **Cuota de YouTube Data API**: 10.000 unidades/día, cada subida de vídeo consume ~1.600 unidades → ~6 subidas/día como techo práctico sin solicitar aumento de cuota. No es un problema para 1-2 episodios/día, pero limita escalar a múltiples canales/idiomas sin gestionar cuota adicional.
8. **RAM insuficiente** puede degradar aún más cualquier intento de Opción B (offload a CPU) — debe confirmarse con el instalador antes de habilitar nada de vídeo IA.
9. **Derivas de licencia en música/SFX** si no se registra el origen de cada asset desde el primer día — riesgo de reclamaciones de copyright/Content ID en las plataformas.
10. **Sin benchmark real todavía** (ver sección 0): existe la posibilidad de que las cifras comunitarias no se repliquen exactamente en tu combinación exacta de drivers/SO/versión de librerías. Por eso el paso obligatorio siguiente es ejecutar el benchmark suite localmente antes de construir Fase 3 en adelante.

---

## 10. PLAN DE IMPLEMENTACIÓN

**FASE 1 — (este documento) Análisis técnico.** ✅ Completado — pendiente de validación con benchmark real.

**FASE 1.5 — BENCHMARK REAL (obligatorio antes de Fase 2 según punto 32 del brief).**
Voy a preparar un `benchmark_suite/` con 5 scripts que debes ejecutar en tu máquina con la RTX 2060:
- `test_01_image.py` — genera 1 imagen SDXL/Flux schnell vía ComfyUI, mide VRAM/tiempo.
- `test_02_voice.py` — genera 20s de audio con Kokoro y Piper, mide tiempo/CPU.
- `test_03_animate.py` — anima una imagen (zoom/parallax) con FFmpeg/Python, mide tiempo.
- `test_04_video.py` — (opcional/experimental) intenta un clip Wan 2.1 1.3B, mide VRAM/tiempo/fallos.
- `test_05_full_render.py` — ensambla un episodio completo de prueba, mide tiempo total y detecta fallos.
Cada test registra VRAM, RAM, tiempo, CPU/GPU%, fallos y una puntuación de calidad subjetiva simple. Con esos resultados confirmamos o ajustamos `RECOMMENDED_PIPELINE`.

**FASE 2 — Instalador automático** (detecta GPU/VRAM/RAM/CPU/CUDA/Python/FFmpeg/espacio, genera el informe HARDWARE COMPATIBILITY real).

**FASES 3–17** — según el orden ya definido en el brief (Story Engine → Character Engine → Image Engine → Animation/Video Engine → Voice Engine → Subtitle Engine → FFmpeg Renderer → QC → Database → Scheduler/n8n → YouTube → TikTok → Instagram → Analytics → Autopilot), respetando el sistema de proveedores/interfaces (`StoryProvider`, `ImageProvider`, `VideoProvider`, `VoiceProvider`, `MusicProvider`, `SubtitleProvider`, `Publisher`) para poder sustituir cualquier modelo sin rehacer el sistema, y los modos `COST_MODE=ZERO/HYBRID` desde el diseño inicial de cada proveedor.

Recomiendo iniciar la solicitud de auditoría de TikTok y revisión de permisos de Instagram **en paralelo, lo antes posible** (Fases 14-15), dado que sus tiempos de aprobación externos son el mayor riesgo de calendario del proyecto y no dependen de nuestro ritmo de desarrollo.

---

## 11. DECISIÓN — RECOMMENDED_PIPELINE

```
RTX 2060 6GB detected.
Full local video generation:
NOT RECOMMENDED (VRAM al límite, 10-15+ min/clip de 3-5s, inviable para producción diaria fiable)

Recommended:
Local LLM (Qwen2.5-7B-Q4 / Phi-4-mini como base segura)
+
SDXL / Flux schnell image generation (ComfyUI, no Automatic1111)
+
2.5D animation (zoom/pan/parallax, CPU/FFmpeg)
+
Kokoro (primario) / Piper (fallback) TTS
+
faster-whisper STT
+
FFmpeg renderer
+
n8n scheduler
+
official publishing APIs (YouTube/TikTok/Instagram)

Experimental fallback (COST_MODE=HYBRID, uso puntual, no bloqueante):
Wan 2.1 T2V-1.3B para 1 escena "hero" — activar solo si el benchmark real
confirma tiempos aceptables en tu máquina.
```

Esta recomendación queda **pendiente de confirmación** con el benchmark real (sección 9 / Fase 1.5). Si tus resultados difieren significativamente de las cifras comunitarias aquí citadas, ajustamos la arquitectura antes de tocar código de producción.
