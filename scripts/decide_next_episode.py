#!/usr/bin/env python3
"""
Lets the LLM itself decide what the next episode is about, instead of
reading a hand-written queue -- this is the piece that makes the show
runnable unattended long-term (e.g. on a Raspberry Pi with nobody curating
a topics file): the model decides whether to continue the series in
progress, wrap it up, start one of the pre-cast roster series (so it still
has a matching hand-drawn mascot -- see assets/characters/), or, once every
roster series has been used, invent a brand-new series and character
entirely on its own.

State lives in content/show_state.json (committed back to the repo each
run, same as content/used_topics.json used to be) so the show has memory of
its own history across runs without any external database.

Usage: python scripts/decide_next_episode.py
Prints one line of JSON on success: {"subject": "..."} -- same contract
scripts/pick_topic.py used, so nothing downstream (cli.py invocation,
overlay_mascot.py, generate_thumbnail.py) needs to change.

Falls back to the old static-queue logic (scripts/pick_topic.py) if the LLM
call or its response is unusable for any reason, so a flaky network call or
a malformed response never breaks an unattended run.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
STATE_PATH = os.path.join(ROOT, "content", "show_state.json")

SHOWRUNNER_SYSTEM_PROMPT = """Eres el showrunner de una serie de microhistorias infantiles en español (60-80 segundos por episodio, para YouTube Shorts/TikTok). Decides tú qué pasa a continuación en el show, como si fueras el guionista jefe de una serie real.

Reglas de continuidad que debes respetar siempre:
1. Si hay una serie "en curso", casi siempre debes continuarla con el siguiente capítulo coherente con lo ya sucedido, a menos que consideres que esta es una buena forma de cerrarla (entre 3 y 6 capítulos totales es un buen rango para un arco completo).
2. Nunca empieces una serie nueva mientras haya una en curso.
3. Al elegir una serie nueva, prioriza siempre una del "reparto disponible" (series con personaje ya dibujado) sobre inventar una completamente nueva -- solo inventa una serie y personaje totalmente nuevos si el reparto disponible está vacío.
4. Si inventas una serie nueva, dale un nombre de serie corto tipo "Nombre - concepto breve" (igual que las existentes) y un personaje protagonista con nombre propio y personalidad clara.

Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, con esta forma exacta:
{
  "action": "continue" | "conclude" | "start_roster" | "start_new",
  "series": "nombre exacto de la serie",
  "chapter_idea": "una frase describiendo qué pasa en este capítulo concreto",
  "new_character_name": "solo si action es start_new, el nombre del protagonista nuevo"
}"""


def _load_state() -> dict:
    with open(STATE_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _save_state(state: dict) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def _active_series(state: dict) -> dict | None:
    for series in state["series"]:
        if series["status"] == "in_progress":
            return series
    return None


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
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object found in LLM response")
    return json.loads(match.group(0))


def _ask_llm(state: dict) -> dict:
    from openai import OpenAI

    api_key = os.environ["GROQ_API_KEY"]
    base_url = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.environ.get("GROQ_MODEL_NAME", "openai/gpt-oss-120b")

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


def _apply_decision(state: dict, decision: dict) -> str:
    action = decision["action"]
    series_name = decision["series"].strip()
    chapter_idea = decision["chapter_idea"].strip()

    if action == "continue" or action == "conclude":
        active = _active_series(state)
        if not active or active["name"] != series_name:
            raise ValueError(f"LLM tried to {action} '{series_name}' but it is not the active series")
        chapter_n = len(active["chapters"]) + 1
        active["chapters"].append({"n": chapter_n, "summary": chapter_idea})
        if action == "conclude":
            active["status"] = "concluded"
    elif action == "start_roster":
        if series_name not in state["roster"] or state["roster"][series_name]["status"] != "not_started":
            raise ValueError(f"LLM tried to start_roster an invalid series: '{series_name}'")
        state["roster"][series_name]["status"] = "in_progress"
        chapter_n = 1
        state["series"].append(
            {"name": series_name, "status": "in_progress", "chapters": [{"n": chapter_n, "summary": chapter_idea}]}
        )
    elif action == "start_new":
        chapter_n = 1
        state["series"].append(
            {"name": series_name, "status": "in_progress", "chapters": [{"n": chapter_n, "summary": chapter_idea}]}
        )
        state["roster"][series_name] = {"mascots": [], "status": "in_progress"}
    else:
        raise ValueError(f"unknown action from LLM: {action}")

    return f"{series_name} - Capitulo {chapter_n}: {chapter_idea}"


def _fallback() -> int:
    print("falling back to the static topics queue (scripts/pick_topic.py)", file=sys.stderr)
    from pick_topic import main as pick_topic_main  # noqa: E402

    return pick_topic_main()


def main() -> int:
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        state = _load_state()
        decision = _ask_llm(state)
        subject = _apply_decision(state, decision)
        _save_state(state)
    except Exception as exc:  # noqa: BLE001 -- any failure here must not break an unattended run
        print(f"LLM-driven episode decision failed: {exc}", file=sys.stderr)
        return _fallback()

    print(json.dumps({"subject": subject}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
