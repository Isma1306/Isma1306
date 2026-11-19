"""GitHub stats card: contributions, commits, stars, longest streak, repos and a 12-month activity strip.

Private contributions are included (the token is yours), but only totals are drawn.
Run directly for just this card, or via build.py for all cards (same height side by side).
"""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from common import CARD_W, DEBUG, PAD, TITLE_H, card, graphql

ACCENT = "#3b82f6"   # activity bars; same blue as the donut's first slice
OUT = Path(__file__).resolve().parent.parent / "assets" / "stats.svg"

PROFILE_QUERY = """
query($cursor: String) {
  viewer {
    contributionsCollection { contributionYears }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
  }
}"""

YEAR_FIELDS = """
    totalCommitContributions
    contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }"""

CELL_H, BARS_H, BARS_LABEL_H = 56, 44, 22


def collect():
    v = graphql(PROFILE_QUERY)["viewer"]
    stars, repos = 0, v["repositories"]
    while True:
        stars += sum(r["stargazerCount"] for r in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        repos = graphql(PROFILE_QUERY, {"cursor": repos["pageInfo"]["endCursor"]})["viewer"]["repositories"]
    now = datetime.now(timezone.utc)
    years = sorted(v["contributionsCollection"]["contributionYears"])
    # One aliased contributionsCollection per year (the API caps each range at one year)
    parts = []
    for y in years:
        to = now.isoformat() if y == now.year else f"{y}-12-31T23:59:59Z"
        parts.append(f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{to}") {{{YEAR_FIELDS}}}')
    per_year = graphql("query { viewer { " + "\n".join(parts) + " } }")["viewer"]

    days = {}
    for y in years:
        for week in per_year[f"y{y}"]["contributionCalendar"]["weeks"]:
            for d in week["contributionDays"]:
                days[date.fromisoformat(d["date"])] = d["contributionCount"]
    this_year = per_year[f"y{now.year}"] if f"y{now.year}" in per_year else None

    stats = {
        "year": now.year,
        "contributions_year": this_year["contributionCalendar"]["totalContributions"] if this_year else 0,
        "commits_year": this_year["totalCommitContributions"] if this_year else 0,
        "contributions_total": sum(per_year[f"y{y}"]["contributionCalendar"]["totalContributions"] for y in years),
        "stars": stars,
        "repos": v["repositories"]["totalCount"],
        "streak_longest": longest_streak(days, now.date()),
        "weeks": weekly(days, now.date()),
    }
    if DEBUG:
        print({k: val for k, val in stats.items() if k != "weeks"})
        print("weekly:", stats["weeks"])
    return stats


def longest_streak(days, today):
    longest = run = 0
    for d in sorted(days):
        if d > today:
            break
        run = run + 1 if days[d] else 0
        longest = max(longest, run)
    return longest


def weekly(days, today, n=52):
    """Contribution totals for the last n 7-day blocks, oldest first."""
    return [sum(days.get(today - timedelta(days=w * 7 + i), 0) for i in range(7)) for w in reversed(range(n))]


def height(_stats=None):
    return TITLE_H + 2 * CELL_H + 12 + BARS_LABEL_H + BARS_H + PAD


def render(s, min_h=0):
    h = max(height(), min_h)
    cells = [
        (f"{s['contributions_year']:,}", f"Contributions in {s['year']}"),
        (f"{s['commits_year']:,}", f"Commits in {s['year']}"),
        (f"{s['stars']:,}", "Stars"),
        (f"{s['streak_longest']}d", "Longest streak"),
        (f"{s['repos']:,}", "Repositories"),
    ]
    col_w = (CARD_W - 2 * PAD) / 3
    body = []
    for i, (value, label) in enumerate(cells):
        x = PAD + (i % 3) * col_w
        y = TITLE_H + (i // 3) * CELL_H
        body.append(f'<text x="{x:.1f}" y="{y + 22}" class="big">{value}</text>'
                    f'<text x="{x:.1f}" y="{y + 40}" class="label">{label}</text>')

    # Activity strip, anchored to the bottom of the card
    base = h - PAD
    body.append(f'<text x="{PAD}" y="{base - BARS_H - 8}" class="label">Last 12 months · '
                f'{sum(s["weeks"]):,} contributions</text>')
    weeks = s["weeks"]
    peak = max(weeks) or 1
    step = (CARD_W - 2 * PAD) / len(weeks)
    for i, n in enumerate(weeks):
        bh = max(2, BARS_H * n / peak)
        opacity = 1 if n else 0.25
        body.append(f'<rect x="{PAD + i * step:.1f}" y="{base - bh:.1f}" width="{step - 2:.1f}" height="{bh:.1f}" '
                    f'rx="1.5" fill="{ACCENT}" fill-opacity="{opacity}"/>')

    label = (f"GitHub stats: {s['contributions_year']} contributions and {s['commits_year']} commits in {s['year']}, "
             f"{s['stars']} stars, {s['repos']} repositories, longest streak {s['streak_longest']} days")
    return card(h, "GitHub stats", "\n".join(body), label)


if __name__ == "__main__":
    stats = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(stats))
    print(f"Wrote {OUT}")
