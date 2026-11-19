"""Shared bits for the profile cards: GitHub GraphQL access and the card frame/theme."""

import json
import os
import sys
import urllib.request

DEBUG = "--debug" in sys.argv  # print what the API returned (local use only: Actions logs are public)
CARD_W = 480                   # every card is this wide, so they line up side by side
PAD = 24
TITLE_H = 56                   # space taken by the card title


def token():
    tok = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not tok:
        sys.exit("Set PROFILE_TOKEN (or GITHUB_TOKEN)")
    return tok


def graphql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {token()}", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


FONT = "'Segoe UI', Ubuntu, sans-serif"
STYLE = f"""
  .card {{ fill: #ffffff; stroke: #d0d7de; }}
  .title {{ font: 600 16px {FONT}; fill: #1f2328; }}
  .name {{ font: 400 13px {FONT}; fill: #1f2328; }}
  .pct, .label, .sub {{ font: 400 13px {FONT}; fill: #59636e; }}
  .label {{ font-size: 12px; }}
  .big {{ font: 600 24px {FONT}; fill: #1f2328; }}
  .seg {{ stroke: #ffffff; stroke-width: 2; stroke-linejoin: round; }}
  @media (prefers-color-scheme: dark) {{
    .card {{ fill: #0d1117; stroke: #30363d; }}
    .seg {{ stroke: #0d1117; }}
    .title, .name, .big {{ fill: #e6edf3; }}
    .pct, .label, .sub {{ fill: #9198a1; }}
  }}"""


def card(h, title, body, label, subtitle=""):
    """Wrap card content in the shared frame. `label` is the accessible description."""
    from html import escape
    sub = (f'<text x="{CARD_W - PAD}" y="36" class="sub" text-anchor="end">{escape(subtitle)}</text>'
           if subtitle else "")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{h}" viewBox="0 0 {CARD_W} {h}" role="img" aria-label="{escape(label)}">
<style>{STYLE}
</style>
<rect class="card" x="0.5" y="0.5" width="{CARD_W - 1}" height="{h - 1}" rx="8"/>
<text x="{PAD}" y="36" class="title">{escape(title)}</text>{sub}
{body}
</svg>
'''
