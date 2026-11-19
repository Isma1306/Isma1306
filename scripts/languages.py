"""Most-used languages donut, across your repos, private ones included.

Only aggregated percentages end up in the SVG; private repo names never leave the API call.
Run directly for just this card, or via build.py for all cards (same height side by side).
"""

import math
import sys
from html import escape
from pathlib import Path

from common import CARD_W, DEBUG, PAD, TITLE_H, card, graphql

TOP_N = 8                      # languages shown; the rest are grouped as "Other"
EXCLUDE = {"HTML", "CSS", "SCSS", "Jupyter Notebook", "Makefile", "Dockerfile", "Shell", "CMake", "ShaderLab", "HLSL"}
# OWNER = your repos. Add "ORGANIZATION_MEMBER", "COLLABORATOR" to count org/shared repos too.
AFFILIATIONS = ["OWNER"]
# Ignore specific languages in specific repos: {"repo-name": {"Language", ...}}
SKIP_REPO_LANGS = {}
# Count several languages as one: {"Language": "Group label"}; the group takes the color in GROUP_COLORS.
MERGE = {"TypeScript": "TS / JS", "JavaScript": "TS / JS"}
GROUP_COLORS = {"TS / JS": "#3178c6"}  # only used when PALETTE = None
# Slice colors by rank (1st, 2nd, ...), picked to stay distinct from each other; "Other" is always gray.
# Set PALETTE = None to use GitHub's language colors instead (some are near-identical, e.g. Dart / Go).
PALETTE = ["#3b82f6", "#22c55e", "#facc15", "#ef4444", "#a855f7", "#f97316", "#14b8a6", "#ec4899"]
#          blue       green      yellow     red        purple     orange     teal       pink
# Score per language = bytes ** SIZE_WEIGHT * repo_count ** COUNT_WEIGHT.
# 1 / 0 = pure bytes (one huge repo dominates); 0.5 / 0.5 balances code size and how often you use it.
SIZE_WEIGHT = 0.5
COUNT_WEIGHT = 0.5
OUT = Path(__file__).resolve().parent.parent / "assets" / "languages.svg"

QUERY = """
query($cursor: String, $aff: [RepositoryAffiliation]) {
  viewer {
    repositories(first: 100, after: $cursor, isFork: false, ownerAffiliations: $aff) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        isPrivate
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}"""

R_OUT, R_IN, ROW_H = 80, 50, 22


def collect():
    """Fetch every repo's languages and return the ranked items: [(name, percent, color), ...]."""
    sizes, counts, colors, cursor = {}, {}, {}, None
    while True:
        page = graphql(QUERY, {"cursor": cursor, "aff": AFFILIATIONS})["viewer"]["repositories"]
        for repo in page["nodes"]:
            if DEBUG:
                langs = ", ".join(f"{e['node']['name']} {e['size']:,}" for e in repo["languages"]["edges"])
                print(f"  {'private' if repo['isPrivate'] else 'public '}  {repo['name']}: {langs or '-'}")
            skip = SKIP_REPO_LANGS.get(repo["name"], set())
            seen = set()  # a repo with both TS and JS counts once for the merged group
            for edge in repo["languages"]["edges"]:
                lang = edge["node"]["name"]
                if lang in EXCLUDE or lang in skip:
                    continue
                name = MERGE.get(lang, lang)
                sizes[name] = sizes.get(name, 0) + edge["size"]
                seen.add(name)
                colors[name] = GROUP_COLORS.get(name) or edge["node"]["color"] or "#8b949e"
            for name in seen:
                counts[name] = counts.get(name, 0) + 1
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    if not sizes:
        sys.exit("No language data returned; check the token's repo access")

    scores = {n: sizes[n] ** SIZE_WEIGHT * counts[n] ** COUNT_WEIGHT for n in sizes}
    total = sum(scores.values())
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    if DEBUG:
        print("\nRanking (after EXCLUDE / SKIP_REPO_LANGS):")
        for i, (n, s) in enumerate(ranked, 1):
            print(f"  {i:2}. {n:<24} {sizes[n]:>10,} bytes {counts[n]:>3} repos  {s / total * 100:5.1f}%"
                  f"{'' if i <= TOP_N else '  -> Other'}")
    return to_items(dict(ranked), colors)


def to_items(scores, colors):
    total = sum(scores.values()) or 1
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top, rest = ranked[:TOP_N], ranked[TOP_N:]
    items = [(n, s / total * 100, PALETTE[i % len(PALETTE)] if PALETTE else colors.get(n, "#8b949e"))
             for i, (n, s) in enumerate(top)]
    if rest:
        items.append(("Other", sum(s for _, s in rest) / total * 100, "#8b949e"))
    return items


def height(items):
    return TITLE_H + max(2 * R_OUT, len(items) * ROW_H) + PAD


def render(items, min_h=0):
    h = max(height(items), min_h)
    legend_h = len(items) * ROW_H
    cx, cy = PAD + R_OUT + 8, TITLE_H + (h - TITLE_H - PAD) / 2   # donut and legend centred in the body

    # Donut: one ring segment per language, clockwise from 12 o'clock
    def point(r, a):
        return cx + r * math.cos(a), cy + r * math.sin(a)

    segs, a0 = [], -math.pi / 2
    for name, pct, color in items:
        a1 = a0 + 2 * math.pi * min(pct, 99.999) / 100
        large = 1 if a1 - a0 > math.pi else 0
        (x0, y0), (x1, y1) = point(R_OUT, a0), point(R_OUT, a1)
        (x2, y2), (x3, y3) = point(R_IN, a1), point(R_IN, a0)
        segs.append(f'<path class="seg" fill="{color}" d="M{x0:.2f},{y0:.2f} A{R_OUT},{R_OUT} 0 {large} 1 {x1:.2f},{y1:.2f} '
                    f'L{x2:.2f},{y2:.2f} A{R_IN},{R_IN} 0 {large} 0 {x3:.2f},{y3:.2f} Z"/>')
        a0 = a1

    # Legend, one column to the right
    legend, lx, rx = [], cx + R_OUT + 40, CARD_W - PAD
    ly0 = cy - legend_h / 2 + ROW_H / 2 + 4
    for i, (name, pct, color) in enumerate(items):
        ly = ly0 + i * ROW_H
        legend.append(
            f'<circle cx="{lx + 5}" cy="{ly - 4:.1f}" r="5" fill="{color}"/>'
            f'<text x="{lx + 18}" y="{ly:.1f}" class="name">{escape(name)}</text>'
            f'<text x="{rx}" y="{ly:.1f}" class="pct" text-anchor="end">{pct:.1f}%</text>'
        )

    label = "Most used languages: " + ", ".join(f"{n} {p:.1f}%" for n, p, _ in items)
    return card(h, "Most used languages", "".join(segs) + "\n" + "".join(legend), label)


if __name__ == "__main__":
    items = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(items))
    print(f"Wrote {OUT}")
