#!/usr/bin/env python3
"""
Generates this project's mascot illustrations (SVG + PNG) as plain vector
shapes -- no third-party art, no image-generation API, fully free and
license-clean. Re-run this after editing CHARACTERS below to regenerate the
PNG overlays used by scripts/overlay_mascot.py.

Usage: python assets/characters/generate_mascots.py
Requires cairosvg (pip install cairosvg); only needed to regenerate assets,
not at workflow runtime -- the committed PNGs are what ships.
"""
import os

import cairosvg

HERE = os.path.dirname(os.path.realpath(__file__))

HEAD_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <defs>
    <radialGradient id="cheek-{key}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{blush}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{blush}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  {extras_back}
  <ellipse cx="200" cy="215" rx="145" ry="130" fill="{skin}"/>
  {extras_front}
  <circle cx="118" cy="255" r="34" fill="url(#cheek-{key})"/>
  <circle cx="282" cy="255" r="34" fill="url(#cheek-{key})"/>
  <ellipse cx="150" cy="205" rx="24" ry="28" fill="{eye}"/>
  <ellipse cx="250" cy="205" rx="24" ry="28" fill="{eye}"/>
  <circle cx="158" cy="195" r="7" fill="#ffffff"/>
  <circle cx="258" cy="195" r="7" fill="#ffffff"/>
  <path d="M 124 170 Q 150 156 176 170" stroke="{brow}" stroke-width="6" fill="none" stroke-linecap="round"/>
  <path d="M 224 170 Q 250 156 276 170" stroke="{brow}" stroke-width="6" fill="none" stroke-linecap="round"/>
  {nose}
  <path d="M 200 265 Q 200 288 176 288 Q 158 288 158 274" stroke="{mouth}" stroke-width="6" fill="none" stroke-linecap="round"/>
  <path d="M 200 265 Q 200 288 224 288 Q 242 288 242 274" stroke="{mouth}" stroke-width="6" fill="none" stroke-linecap="round"/>
  {freckles}
  {collar}
</svg>
"""


def _freckles(cx: int, color: str = "#c9714a") -> str:
    offsets = [(-58, 40), (-64, 55), (58, 40), (64, 55)]
    dots = "".join(
        f'<circle cx="{cx + dx}" cy="{240 + dy}" r="3" fill="{color}"/>'
        for dx, dy in offsets
    )
    return dots


CHARACTERS = {
    # Tobías -- "Tobías y el barco de papel"
    "tobias_boy": dict(
        skin="#f4c99b",
        eye="#2b1a12",
        brow="#6b4226",
        mouth="#2b1a12",
        blush="#ff9f7a",
        nose='<path d="M 192 245 Q 200 258 208 245" stroke="#c98a5a" stroke-width="5" fill="none" stroke-linecap="round"/>',
        freckles=_freckles(200),
        extras_back="",
        extras_front=(
            '<path d="M 90 170 Q 90 40 200 40 Q 310 40 310 170 Q 300 130 200 120 Q 100 130 90 170 Z" fill="#6b4226"/>'
            '<path d="M 190 40 L 205 12 L 212 45 Z" fill="#6b4226"/>'
        ),
        collar='<path d="M 130 330 Q 200 300 270 330 L 270 400 L 130 400 Z" fill="#3f7bbf"/>',
    ),
    # Pipo -- "El elefante invisible"
    "pipo_elephant": dict(
        skin="#aab9cc",
        eye="#2b1a12",
        brow="#5c6a7d",
        mouth="#3a4657",
        blush="#ff9f9f",
        nose="",
        freckles="",
        extras_back=(
            '<ellipse cx="70" cy="220" rx="55" ry="70" fill="#aab9cc"/>'
            '<ellipse cx="330" cy="220" rx="55" ry="70" fill="#aab9cc"/>'
            '<ellipse cx="70" cy="220" rx="34" ry="48" fill="#8f9fb3"/>'
            '<ellipse cx="330" cy="220" rx="34" ry="48" fill="#8f9fb3"/>'
        ),
        extras_front=(
            '<path d="M 190 260 Q 180 320 195 350 Q 205 360 215 350 Q 210 330 205 300 Q 205 275 195 260 Z" '
            'fill="#aab9cc"/>'
        ),
        collar="",
    ),
    # Mar -- "La isla de luna llena" (hermana)
    "mar_sister": dict(
        skin="#f4c99b",
        eye="#2b1a12",
        brow="#241a12",
        mouth="#2b1a12",
        blush="#ff9f7a",
        nose='<path d="M 192 245 Q 200 258 208 245" stroke="#c98a5a" stroke-width="5" fill="none" stroke-linecap="round"/>',
        freckles="",
        extras_back="",
        extras_front=(
            '<path d="M 85 175 Q 85 40 200 40 Q 315 40 315 175 Q 300 125 200 115 Q 100 125 85 175 Z" fill="#241a12"/>'
            '<path d="M 90 175 Q 70 230 78 300 Q 95 285 100 220 Z" fill="#241a12"/>'
            '<path d="M 310 175 Q 330 230 322 300 Q 305 285 300 220 Z" fill="#241a12"/>'
            '<path d="M 150 130 L 175 100 L 165 135 Z" fill="#d1385a"/>'
        ),
        collar='<path d="M 130 330 Q 200 300 270 330 L 270 400 L 130 400 Z" fill="#e0577a"/>',
    ),
    # Leo -- "La isla de luna llena" (hermano)
    "leo_brother": dict(
        skin="#e8b483",
        eye="#2b1a12",
        brow="#3a2a1a",
        mouth="#2b1a12",
        blush="#ff9f7a",
        nose='<path d="M 192 245 Q 200 258 208 245" stroke="#b5754a" stroke-width="5" fill="none" stroke-linecap="round"/>',
        freckles=_freckles(200),
        extras_back="",
        extras_front=(
            '<path d="M 88 175 Q 88 45 200 45 Q 312 45 312 175 Q 298 120 200 110 Q 102 120 88 175 Z" fill="#4a3a26"/>'
        ),
        collar='<path d="M 130 330 Q 200 300 270 330 L 270 400 L 130 400 Z" fill="#4c9e6d"/>',
    ),
    # Rey Teodoro -- "El rey que aprendió a escuchar"
    "teodoro_king": dict(
        skin="#f0c8a0",
        eye="#2b1a12",
        brow="#c9c9c9",
        mouth="#2b1a12",
        blush="#ff9f9f",
        nose='<path d="M 192 245 Q 200 260 208 245" stroke="#c98a5a" stroke-width="5" fill="none" stroke-linecap="round"/>',
        freckles="",
        extras_back="",
        extras_front=(
            '<path d="M 130 160 L 150 100 L 180 145 L 200 90 L 220 145 L 250 100 L 270 160 Z" fill="#e8b923"/>'
            '<circle cx="150" cy="100" r="8" fill="#c0392b"/>'
            '<circle cx="200" cy="90" r="8" fill="#3b6fc9"/>'
            '<circle cx="250" cy="100" r="8" fill="#c0392b"/>'
            '<path d="M 130 240 Q 200 260 270 240" stroke="#c9c9c9" stroke-width="7" fill="none" stroke-linecap="round"/>'
        ),
        collar='<path d="M 120 330 Q 200 295 280 330 L 280 400 L 120 400 Z" fill="#6a3fa0"/>',
    ),
    # Alba -- "El rey que aprendió a escuchar" (niña del pueblo)
    "alba_villager": dict(
        skin="#e8b483",
        eye="#2b1a12",
        brow="#3a2a1a",
        mouth="#2b1a12",
        blush="#ff9f7a",
        nose='<path d="M 192 245 Q 200 258 208 245" stroke="#b5754a" stroke-width="5" fill="none" stroke-linecap="round"/>',
        freckles=_freckles(200),
        extras_back="",
        extras_front=(
            '<path d="M 88 175 Q 88 45 200 45 Q 312 45 312 175 Q 298 120 200 110 Q 102 120 88 175 Z" fill="#4a3a26"/>'
            '<path d="M 92 175 Q 72 235 82 310 Q 100 292 104 225 Z" fill="#4a3a26"/>'
            '<path d="M 308 175 Q 328 235 318 310 Q 300 292 296 225 Z" fill="#4a3a26"/>'
        ),
        collar='<path d="M 130 330 Q 200 300 270 330 L 270 400 L 130 400 Z" fill="#4c9e6d"/>',
    ),
}


# --- "Object with a body" mascots -----------------------------------------
# The eye-catching, scroll-stopping style the user asked for (think: a
# coffee cup with human arms and legs) -- an everyday object gets a face,
# arms and legs and just walks/talks like a person. Taller canvas than the
# bust template above so there's room for a standing body. Each one is
# still hand-drawn plain SVG shapes, no third-party art or image API.
BODY_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 520" width="400" height="520">
  {legs}
  {body}
  {arms}
  {face}
</svg>
"""

OBJECT_CHARACTERS = {
    # Toby -- the talking paper boat, "Tobías y el barco de papel". A folded
    # paper hull with a face, noodle arms and little legs -- replaces the
    # plain boy bust with a proper object-with-a-body hook character.
    "toby_paperboat": dict(
        legs=(
            '<path d="M 165 400 L 155 470 L 185 470 L 190 405 Z" fill="#d8b892"/>'
            '<ellipse cx="163" cy="478" rx="26" ry="12" fill="#7a5230"/>'
            '<path d="M 235 400 L 245 465 L 215 470 L 210 405 Z" fill="#d8b892"/>'
            '<ellipse cx="237" cy="475" rx="26" ry="12" fill="#7a5230"/>'
        ),
        body=(
            '<path d="M 60 300 L 200 150 L 340 300 L 300 400 L 100 400 Z" fill="#f5ead7"/>'
            '<path d="M 60 300 L 340 300 L 300 330 L 100 330 Z" fill="#e6d5b8"/>'
            '<path d="M 200 150 L 200 300" stroke="#d8c39c" stroke-width="4"/>'
            '<path d="M 200 150 L 260 60 L 260 210 Z" fill="#e0577a"/>'
        ),
        arms=(
            '<path d="M 100 330 Q 40 320 25 260" stroke="#d8b892" stroke-width="24" fill="none" stroke-linecap="round"/>'
            '<circle cx="22" cy="252" r="20" fill="#d8b892"/>'
            '<path d="M 300 330 Q 370 340 385 390" stroke="#d8b892" stroke-width="24" fill="none" stroke-linecap="round"/>'
            '<circle cx="388" cy="396" r="20" fill="#d8b892"/>'
        ),
        face=(
            '<circle cx="170" cy="255" r="20" fill="#2b1a12"/>'
            '<circle cx="176" cy="247" r="6" fill="#ffffff"/>'
            '<circle cx="250" cy="255" r="20" fill="#2b1a12"/>'
            '<circle cx="256" cy="247" r="6" fill="#ffffff"/>'
            '<circle cx="130" cy="270" r="18" fill="#ff9f7a" opacity="0.5"/>'
            '<circle cx="290" cy="270" r="18" fill="#ff9f7a" opacity="0.5"/>'
            '<path d="M 190 290 Q 210 310 230 290" stroke="#2b1a12" stroke-width="6" fill="none" stroke-linecap="round"/>'
        ),
    ),
}


def main() -> None:
    for key, params in CHARACTERS.items():
        svg = HEAD_TEMPLATE.format(key=key, **params)
        svg_path = os.path.join(HERE, f"{key}.svg")
        png_path = os.path.join(HERE, f"{key}.png")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=400, output_height=400)
        print(f"generated {svg_path} and {png_path}")

    for key, params in OBJECT_CHARACTERS.items():
        svg = BODY_TEMPLATE.format(**params)
        svg_path = os.path.join(HERE, f"{key}.svg")
        png_path = os.path.join(HERE, f"{key}.png")
        with open(svg_path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=400, output_height=520)
        print(f"generated {svg_path} and {png_path}")


if __name__ == "__main__":
    main()
