#!/usr/bin/env python3
"""
Lets the LLM itself run the show as a "frutinovela"-style micro-series
showrunner: recurring characters with a persistent bible, relationships,
hidden secrets planted and paid off across episodes, open plot threads, and
endings that vary in shape (resolution / twist / reveal / cliffhanger)
instead of always the same "moraleja" close. This is also what makes the
show runnable unattended long-term (e.g. on a Raspberry Pi with nobody
curating a topics file): the model decides whether to continue the series
in progress, wrap it up, start one of the pre-cast roster series (so it
still has a matching hand-drawn mascot -- see assets/characters/), or, once
every roster series has been used, invent a brand-new series and character
entirely on its own.

Character design note: only NEW characters get a proposed visual design
(a short "diseño_visual" brief in the character bible) -- established
characters (Luna, and anything with a mascot_file already set) must never
have their design changed. New designs must NOT default to "generic
humanoid animal": the brief asks the LLM to pick a genuinely varied, odd,
memorable silhouette per the object/animal/food-becomes-a-character
principle (an object as literal torso, exaggerated limbs, floating with no
legs, animal/human feature mixes, etc.) -- the same idea already used for
toby_paperboat.png. The LLM can only describe this in text; turning that
brief into an actual SVG/PNG mascot is still a manual step (see
assets/characters/generate_mascots.py) done when a new character actually
appears in a real run.

State lives in content/show_state.json (committed back to the repo each
run, same as content/used_topics.json used to be) so the show has memory of
its own history across runs without any external database.

Usage: python scripts/decide_next_episode.py
Prints one line of JSON on success: {"subject": "..."} -- same contract
scripts/pick_topic.py used, so nothing downstream (cli.py invocation,
overlay_mascot.py, generate_thumbnail.py) needs to change. Also renders
content/system_prompt.txt (from content/system_prompt_template.txt) with
this episode's character bible, secrets and ending-type context baked in,
so cli.py's --custom-system-prompt automatically reflects it without any
workflow changes.

Falls back to the old static-queue logic (scripts/pick_topic.py) if the LLM
call or its response is unusable for any reason, so a flaky network call or
a malformed response never breaks an unattended run.
"""
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE_PATH = os.path.join(ROOT, "content", "show_state.json")
PROMPT_TEMPLATE_PATH = os.path.join(ROOT, "content", "system_prompt_template.txt")
PROMPT_OUTPUT_PATH = os.path.join(ROOT, "content", "system_prompt.txt")

ENDING_INSTRUCTIONS = {
    "resolucion": (
        "El problema de este capítulo se resuelve por completo aquí. Cierra "
        "con sensación de historia terminada, sin gancho hacia otro capítulo."
    ),
    "sorpresa": (
        "Termina con un giro divertido o inesperado que resuelve el "
        "conflicto de forma que nadie esperaba, dejando al espectador con "
        "una sonrisa."
    ),
    "revelacion": (
        "La última frase revela algo que cambia cómo entendemos lo que "
        "pasó antes en este capítulo (sobre un personaje, un objeto o un "
        "secreto). No lo resuelvas del todo, solo revélalo."
    ),
    "cliffhanger": (
        "La última frase debe dejar una pregunta sin responder o una "
        "amenaza/sorpresa asomando, sin decir literalmente \"continuará\". "
        "Debe sonar como parte natural de la historia, no como un anuncio."
    ),
}

SHOWRUNNER_SYSTEM_PROMPT = """Eres el showrunner de "El Reino de las Fábulas", una micro-serie episódica de animales/objetos con personalidad, al estilo "frutinovela": personajes recurrentes, relaciones que evolucionan, secretos que se plantan y se revelan más adelante, tramas que quedan abiertas y giros que tienen sentido porque están conectados con algo anterior. Decides tú qué pasa a continuación, como el guionista jefe de una serie real.

Reglas de continuidad que debes respetar siempre:
1. Si hay una serie "en curso", casi siempre debes continuarla con el siguiente capítulo coherente con lo ya sucedido, a menos que consideres que esta es una buena forma de cerrarla (entre 3 y 6 capítulos totales es un buen rango para un arco completo).
2. Nunca empieces una serie nueva mientras haya una en curso.
3. Al elegir una serie nueva, prioriza siempre una del "reparto disponible" (series con personaje ya dibujado) sobre inventar una completamente nueva -- solo inventa una serie y personaje totalmente nuevos si el reparto disponible está vacío.
4. Nunca cambies la especie, el nombre, la personalidad o el diseño visual de un personaje ya existente (aparece en "personajes establecidos" más abajo).
5. No es obligatorio usar un secreto o trama abierta en cada capítulo, pero cuando tenga sentido, planta uno nuevo o resuelve uno existente -- esto es lo que da continuidad real a la serie, más que una moraleja.
6. Varía el tipo de final entre capítulos: no repitas siempre "cliffhanger". A veces cierra del todo (resolucion), a veces sorprende (sorpresa), a veces revela algo (revelacion), y otras veces sí deja un gancho (cliffhanger).

DISEÑO DE PERSONAJES NUEVOS (solo aplica si action=start_new): tu única tarea aquí es INVENTAR Y DESCRIBIR EN TEXTO el concepto visual -- nunca generas ni dibujas nada, eso lo hace un humano después a partir de tu descripción. El personaje protagonista de una serie nueva puede ser un animal, un objeto o un alimento con personalidad. NO uses siempre la misma fórmula de "animal con cuerpo humano". Sé variado y memorable: un objeto puede ser literalmente su propio torso con piernas humanas pegadas (como una taza de café con piernas), un personaje puede tener brazos exagerados o piernas larguísimas, otro puede flotar sin piernas, otro puede mezclar rasgos de animal y persona de forma extraña. La pregunta clave es: "¿qué diseño visual raro, divertido y memorable tendría este personaje si fuera protagonista de una microserie, reconocible en un segundo por su silueta?".

En el campo "diseño_visual" escribe una descripción DETALLADA en varias frases (no una sola línea), al estilo de este ejemplo real:
"Cafecito es una taza de café viviente. La propia taza constituye su torso. Tiene dos brazos humanos pequeños unidos a los laterales. Tiene dos piernas humanas delgadas. Lleva zapatos diminutos. Tiene ojos y boca expresivos integrados visualmente en la taza. La espuma del café tiene un pequeño dibujo de corazón. Su diseño es rechoncho, adorable y ligeramente absurdo. Su silueta debe permitir reconocer inmediatamente que es una taza de café."
Cubre: qué objeto/animal/alimento es la base, qué parte es el torso, cómo son los brazos, cómo son las piernas (o si no tiene y flota), rasgos faciales, algún detalle distintivo pequeño, y por qué su silueta se reconoce al instante.

Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, con esta forma exacta (usa null en los campos opcionales que no apliquen, nunca los omitas):
{
  "action": "continue" | "conclude" | "start_roster" | "start_new",
  "series": "nombre exacto de la serie",
  "chapter_idea": "una frase describiendo qué pasa en este capítulo concreto",
  "tipo_final": "resolucion" | "sorpresa" | "revelacion" | "cliffhanger",
  "new_character_name": "solo si action es start_new, el nombre del protagonista nuevo",
  "diseño_visual": "solo si action es start_new, la descripción del diseño visual siguiendo las reglas de arriba",
  "personalidad_nueva": "solo si action es start_new, personalidad y forma de hablar del protagonista nuevo",
  "plantar_secreto": "un secreto nuevo y oculto que insinúas en este capítulo sin revelarlo del todo, o null",
  "resolver_secreto": "el texto exacto de un secreto de la lista 'secretos ocultos' que revelas en este capítulo, o null",
  "nueva_trama_abierta": "una pregunta o problema que queda pendiente para el futuro, o null",
  "trama_resuelta": "el texto exacto de una trama de la lista 'tramas abiertas' que se resuelve en este capítulo, o null"
}"""


def _load_state() -> dict:
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        state = json.load(fh)
    state.setdefault("characters", {})
    state.setdefault("secretos_ocultos", [])
    state.setdefault("tramas_abiertas", [])
    state.setdefault("objetos_importantes", [])
    return state


def _save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def _active_series(state: dict) -> dict | None:
    for series in state["series"]:
        if series["status"] == "in_progress":
            return series
    return None


def _series_characters(state: dict, series_name: str) -> dict:
    """Characters belonging to this series (by simple name-prefix match)."""
    first_word = re.split(r"[ ,]+", series_name.strip())[0]
    return {
        name: bio
        for name, bio in state["characters"].items()
        if name == first_word or bio.get("series") == series_name
    }


def _build_user_prompt(state: dict) -> str:
    active = _active_series(state)
    lines = []
    if active:
        lines.append(f"Serie en curso: {active['name']}")
        for chapter in active["chapters"]:
            lines.append(f"  Capitulo {chapter['n']}: {chapter['summary']}")
        lines.append(
            "Decide si el siguiente capitulo (continue) o si este es el capitulo final que cierra el arco (conclude)."
        )
        chars = _series_characters(state, active["name"])
        if chars:
            lines.append("Personajes establecidos de esta serie (no cambiar su diseño ni personalidad):")
            for name, bio in chars.items():
                lines.append(f"  - {name}: {bio.get('personalidad', '')}")
    else:
        available = [
            name
            for name, info in state["roster"].items()
            if info["status"] == "not_started"
        ]
        concluded_new = [
            s["name"] for s in state["series"] if s["status"] == "concluded"
        ]
        lines.append("No hay ninguna serie en curso ahora mismo.")
        if available:
            lines.append("Reparto disponible (con personaje ya dibujado): " + ", ".join(available))
            lines.append("Usa action=start_roster con una de esas series exactamente.")
        else:
            lines.append("El reparto disponible esta agotado -- inventa una serie y personaje nuevos con action=start_new.")
        if concluded_new:
            lines.append("Series ya emitidas y cerradas (no las repitas): " + ", ".join(concluded_new))

    if state["secretos_ocultos"]:
        lines.append("Secretos ocultos todavía sin revelar (puedes revelar uno con resolver_secreto, usando el texto EXACTO):")
        for secret in state["secretos_ocultos"]:
            lines.append(f"  - {secret}")
    if state["tramas_abiertas"]:
        lines.append("Tramas abiertas pendientes (puedes resolver una con trama_resuelta, usando el texto EXACTO):")
        for thread in state["tramas_abiertas"]:
            lines.append(f"  - {thread}")

    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(match.group(0))


def _ask_llm(state: dict) -> dict:
    from openai import OpenAI

    api_key = os.environ["GROQ_API_KEY"]
    # `or` (not a second os.environ.get() arg) on purpose: the workflow's
    # `env:` block always sets these two keys, even when the underlying repo
    # variable is unset -- GitHub Actions then sets the env var to an empty
    # string rather than omitting it. os.environ.get(name, default) only
    # falls back when the key is *missing*, so an empty string was winning
    # over the default and handing the OpenAI client an invalid base_url/
    # model, silently breaking every LLM-driven decision since this script
    # was added.
    base_url = os.environ.get("GROQ_BASE_URL") or "https://api.groq.com/openai/v1"
    model = os.environ.get("GROQ_MODEL_NAME") or "openai/gpt-oss-120b"

    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SHOWRUNNER_SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(state)},
        ],
        temperature=0.9,
    )
    content = response.choices[0].message.content or ""
    return _extract_json(content)


def _apply_secrets_and_threads(state: dict, decision: dict) -> None:
    plant = decision.get("plantar_secreto")
    if plant:
        state["secretos_ocultos"].append(str(plant).strip())
    resolve = decision.get("resolver_secreto")
    if resolve and resolve in state["secretos_ocultos"]:
        state["secretos_ocultos"].remove(resolve)

    new_thread = decision.get("nueva_trama_abierta")
    if new_thread:
        state["tramas_abiertas"].append(str(new_thread).strip())
    resolved_thread = decision.get("trama_resuelta")
    if resolved_thread and resolved_thread in state["tramas_abiertas"]:
        state["tramas_abiertas"].remove(resolved_thread)


def _apply_decision(state: dict, decision: dict) -> tuple[str, str, str]:
    """Returns (subject, series_name, tipo_final)."""
    action = decision["action"]
    series_name = decision["series"].strip()
    chapter_idea = decision["chapter_idea"].strip()
    tipo_final = decision.get("tipo_final") or "cliffhanger"
    if tipo_final not in ENDING_INSTRUCTIONS:
        tipo_final = "cliffhanger"

    if action == "continue" or action == "conclude":
        active = _active_series(state)
        if not active or active["name"] != series_name:
            raise ValueError(f"LLM tried to {action} '{series_name}' but it is not the active series")
        chapter_n = len(active["chapters"]) + 1
        active["chapters"].append({"n": chapter_n, "summary": chapter_idea, "tipo_final": tipo_final})
        if action == "conclude":
            active["status"] = "concluded"
    elif action == "start_roster":
        if series_name not in state["roster"] or state["roster"][series_name]["status"] != "not_started":
            raise ValueError(f"LLM tried to start_roster an invalid series: '{series_name}'")
        state["roster"][series_name]["status"] = "in_progress"
        chapter_n = 1
        state["series"].append(
            {"name": series_name, "status": "in_progress",
             "chapters": [{"n": chapter_n, "summary": chapter_idea, "tipo_final": tipo_final}]}
        )
    elif action == "start_new":
        chapter_n = 1
        state["series"].append(
            {"name": series_name, "status": "in_progress",
             "chapters": [{"n": chapter_n, "summary": chapter_idea, "tipo_final": tipo_final}]}
        )
        state["roster"][series_name] = {"mascots": [], "status": "in_progress"}
        char_name = str(decision.get("new_character_name") or series_name).strip()
        state["characters"][char_name] = {
            "series": series_name,
            "personalidad": str(decision.get("personalidad_nueva") or "").strip(),
            "diseño_visual": str(decision.get("diseño_visual") or "").strip(),
            "relaciones": {},
            "mascot_file": None,
            "pendiente_de_ilustrar": True,
        }
    else:
        raise ValueError(f"unknown action from LLM: {action}")

    _apply_secrets_and_threads(state, decision)
    return f"{series_name} - Capitulo {chapter_n}: {chapter_idea}", series_name, tipo_final


def _render_system_prompt(state: dict, series_name: str, tipo_final: str) -> None:
    with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
        template = fh.read()

    chars = _series_characters(state, series_name)
    if chars:
        char_lines = ["Personajes de este capítulo (mantén su personalidad y forma de hablar):"]
        for name, bio in chars.items():
            speech = bio.get("rasgo_de_habla") or ""
            personality = bio.get("personalidad", "")
            char_lines.append(
                f"- {name}: {personality}" + (f" Forma de hablar: {speech}." if speech else "")
            )
        characters_block = "\n".join(char_lines)
    else:
        characters_block = ""

    secrets_hint = ""
    if state["secretos_ocultos"] and random.random() < 0.4:
        secrets_hint = (
            "Puedes insinuar sutilmente, sin explicarlo del todo, este elemento "
            f"misterioso si encaja: {random.choice(state['secretos_ocultos'])}"
        )
    threads_hint = ""
    if state["tramas_abiertas"] and random.random() < 0.4:
        threads_hint = (
            "Trama pendiente que puedes retomar si encaja de forma natural: "
            f"{random.choice(state['tramas_abiertas'])}"
        )

    rendered = template.format(
        ending_type_instruction=ENDING_INSTRUCTIONS[tipo_final],
        characters_block=characters_block,
        secrets_hint=secrets_hint,
        open_threads_hint=threads_hint,
    )
    # Collapse the blank lines left by empty optional sections so the final
    # prompt doesn't look sparse/broken when there are no secrets/threads yet.
    rendered = re.sub(r"\n{3,}", "\n\n", rendered)
    with open(PROMPT_OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(rendered)


def _fallback() -> int:
    print("falling back to the static topics queue (scripts/pick_topic.py)", file=sys.stderr)
    from pick_topic import main as pick_topic_main  # noqa: E402

    return pick_topic_main()


def main() -> int:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        state = _load_state()
        decision = _ask_llm(state)
        subject, series_name, tipo_final = _apply_decision(state, decision)
        _render_system_prompt(state, series_name, tipo_final)
        _save_state(state)
    except Exception as exc:  # noqa: BLE001 -- any failure here must not break an unattended run
        print(f"LLM-driven episode decision failed: {exc}", file=sys.stderr)
        return _fallback()

    print(json.dumps({"subject": subject}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
