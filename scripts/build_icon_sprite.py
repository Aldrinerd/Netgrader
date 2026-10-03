# scripts/build_icon_sprite.py
"""
Build static/icons/sprite.svg from Tabler Icons (MIT), outline style.

Run once on a developer machine with internet access, then commit the output:

    npm pack @tabler/icons@3        # downloads tabler-icons-<version>.tgz
    tar -xzf tabler-icons-*.tgz     # extracts ./package/icons/outline/*.svg
    python scripts/build_icon_sprite.py package/icons/outline <version>

Lab PCs only ever load the committed sprite.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "icons", "sprite.svg")

# Sprite id (what the UI asks for) -> Tabler outline icon file name.
ICONS = {
    "topology": "topology-star-3",
    "instructor": "school",
    "grading": "checklist",
    "display": "typography",
    "ai": "cpu",
    "upload": "upload",
    "file": "file-text",
    "folder": "folder-open",
    "alert": "alert-triangle",
    "check": "circle-check",
    "x": "circle-x",
    "download": "download",
    "copy": "copy",
    "send": "send",
    "report": "report-analytics",
    "shield": "shield-check",
    "network": "network",
    "map": "map",
    "settings": "settings",
    "chart": "chart-bar",
    "search": "search",
    "tag": "tag",
    "pin": "map-pin",
    "info": "info-circle",
    "generate": "file-plus",
    "refresh": "refresh",
    "fit": "arrows-maximize",
}

BOUNDING_BOX = re.compile(r'<path\s+stroke="none"\s+d="M0 0h24v24H0z"\s+fill="none"\s*/>')


def main(src_dir: str, version: str) -> None:
    symbols = []
    for sprite_id, tabler in sorted(ICONS.items()):
        path = os.path.join(src_dir, f"{tabler}.svg")
        if not os.path.isfile(path):
            sys.exit(f"missing Tabler icon '{tabler}' (for '{sprite_id}') in {src_dir}")
        svg = open(path, encoding="utf-8").read()
        inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
        inner = BOUNDING_BOX.sub("", inner).strip()
        inner = re.sub(r"\s+", " ", inner)
        symbols.append(
            f'  <symbol id="{sprite_id}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{inner}</symbol>'
        )
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"<!-- Tabler Icons {version} (MIT), outline. Built by scripts/build_icon_sprite.py -->\n")
        f.write('<svg xmlns="http://www.w3.org/2000/svg">\n' + "\n".join(symbols) + "\n</svg>\n")
    print(f"wrote {OUT}: {len(symbols)} icons")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: build_icon_sprite.py <tabler outline dir> <version>")
    main(sys.argv[1], sys.argv[2])
