"""Render the animated profile card (matrix portrait + neofetch-style info).

Reads the pre-computed portrait brightness grid from assets/portrait.json and,
when GITHUB_TOKEN is set, live GitHub stats. Writes dark and light SVGs into
assets/. Runs daily from .github/workflows/profile-card.yml.
"""
import json
import os
import random
import urllib.request
from html import escape

USER = "khojiakbarr"
CELL_W, CELL_H = 5.6, 9.3
PORTRAIT_X, PORTRAIT_Y = 28, 34
INFO_X, LINE_H = 520, 21
WIDTH, HEIGHT = 1000, 560
LEVELS = 10  # opacity buckets, keeps the SVG small
RAMP = [".:", ":-", "=+", "*o", "x%", "#8", "@&"]

THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "key": "#22d3ee", "text": "#c9d1d9",
             "muted": "#8b949e", "accent": "#6366f1", "glyph": "#2ee6a8"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "key": "#0e7490", "text": "#1f2328",
              "muted": "#656d76", "accent": "#4f46e5", "glyph": "#047857"},
}

INFO = [
    ("title", "khojiakbar@github"),
    ("rule", ""),
    ("kv", "Role", "Frontend & Mobile Developer @ 4DX"),
    ("kv", "Location", "Tashkent, Uzbekistan"),
    ("kv", "Uptime", "2 years in production"),
    ("kv", "Building", "RopAI — AI sales assistant"),
    ("gap",),
    ("kv", "Frontend", "React, Next.js, TypeScript, Tailwind"),
    ("kv", "Mobile", "React Native, Expo"),
    ("kv", "Backend", "NestJS, Node.js, PostgreSQL, Prisma"),
    ("kv", "AI", "Gemini, Vertex AI, MCP, n8n"),
    ("kv", "DevOps", "Docker, CI/CD, Nginx, Vercel"),
    ("gap",),
    ("kv", "Projects", "D-Clinics · CliniCall · RopAI"),
    ("kv", "Certified", "HackerRank Software Engineer"),
    ("gap",),
    ("stats",),
    ("gap",),
    ("kv", "Contact", "khojiakbar.uz · t.me/khojiakbar_developer"),
]

STATS_QUERY = """query($login: String!, $cursor: String) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
  }
}"""


def fetch_stats():
    """Return repos/stars/followers/contributions, or None without a token."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    stars, cursor, user = 0, None, None
    while True:
        body = json.dumps({"query": STATS_QUERY, "variables": {"login": USER, "cursor": cursor}})
        req = urllib.request.Request("https://api.github.com/graphql", data=body.encode(),
                                     headers={"Authorization": f"bearer {token}"})
        user = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]
        repos = user["repositories"]
        stars += sum(node["stargazerCount"] for node in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    return {
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "contributions": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
    }


def portrait(grid):
    """One <text> per row; runs of equal brightness share a <tspan>."""
    rng = random.Random(42)
    rows = []
    for y, row in enumerate(grid):
        spans, x = [], 0
        while x < len(row):
            level = round(row[x] * LEVELS)
            start = x
            while x < len(row) and round(row[x] * LEVELS) == level:
                x += 1
            if level == 0:
                continue
            # denser glyphs for brighter cells: ink coverage carries the tone,
            # opacity smooths it; random picks within a band keep the matrix feel
            band = RAMP[min(len(RAMP) - 1, level * len(RAMP) // (LEVELS + 1))]
            chars = "".join(escape(rng.choice(band)) for _ in range(x - start))
            xs = " ".join(f"{PORTRAIT_X + i * CELL_W:.1f}" for i in range(start, x))
            spans.append(f'<tspan x="{xs}" fill-opacity="{level / LEVELS:.1f}">{chars}</tspan>')
        if spans:
            rows.append(f'<text class="p" y="{PORTRAIT_Y + (y + 1) * CELL_H:.1f}" '
                        f'style="animation-delay:{y * 0.035:.2f}s">{"".join(spans)}</text>')
    return "\n".join(rows)


def info_lines(stats):
    """Neofetch-style lines; each fades in after the portrait has drawn."""
    out, y, i = [], 58, 0
    for item in INFO:
        kind = item[0]
        delay = f"animation-delay:{1.7 + i * 0.09:.2f}s"
        if kind == "title":
            out.append(f'<text class="l t" x="{INFO_X}" y="{y}" style="{delay}">'
                       f'<tspan class="a">khojiakbar</tspan><tspan class="m">@</tspan>'
                       f'<tspan class="a">github</tspan></text>')
        elif kind == "rule":
            out.append(f'<text class="l m" x="{INFO_X}" y="{y}" style="{delay}">{"─" * 44}</text>')
        elif kind == "kv":
            out.append(f'<text class="l" x="{INFO_X}" y="{y}" style="{delay}">'
                       f'<tspan class="k">{escape(item[1])}:</tspan> {escape(item[2])}</text>')
        elif kind == "stats":
            if stats:
                value = f'{stats["repos"]} repos · {stats["followers"]} followers'
                if stats["stars"] >= 10:
                    value += f' · {stats["stars"]} stars'
                out.append(f'<text class="l" x="{INFO_X}" y="{y}" style="{delay}">'
                           f'<tspan class="k">GitHub:</tspan> {value}</text>')
                y += LINE_H; i += 1
                delay = f"animation-delay:{1.7 + i * 0.09:.2f}s"
                out.append(f'<text class="l" x="{INFO_X}" y="{y}" style="{delay}">'
                           f'<tspan class="k">Commits:</tspan> {stats["contributions"]:,} contributions this year</text>')
            else:
                y -= LINE_H
        y += LINE_H if kind != "gap" else LINE_H // 2
        i += 1
    end = 1.7 + i * 0.09
    swatches = "".join(f'<rect x="{INFO_X + n * 26}" y="{y + 4}" width="22" height="12" rx="2" fill="{c}"/>'
                       for n, c in enumerate(["#6366f1", "#22d3ee", "#2ee6a8", "#f59e0b", "#ef4444", "#a855f7"]))
    out.append(f'<g class="l" style="animation-delay:{end:.2f}s">{swatches}'
               f'<rect class="cur" x="{INFO_X + 6 * 26 + 6}" y="{y + 2}" width="9" height="16"/></g>')
    return "\n".join(out)


def render(theme, grid, stats):
    c = THEMES[theme]
    portrait_h = len(grid) * CELL_H
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">
<style>
text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace; }}
.p {{ font-size: 9.3px; fill: {c["glyph"]}; opacity: 0; animation: in .25s ease-out forwards; }}
.l {{ font-size: 14.5px; fill: {c["text"]}; opacity: 0; animation: slide .35s ease-out forwards; }}
.t {{ font-size: 17px; font-weight: 700; }}
.a {{ fill: {c["accent"]}; }} .k {{ fill: {c["key"]}; font-weight: 700; }} .m {{ fill: {c["muted"]}; }}
.cur {{ fill: {c["key"]}; animation: blink 1s step-end infinite; }}
.scan {{ fill: url(#beam); animation: scan 1.8s ease-in-out forwards; }}
@keyframes in {{ to {{ opacity: 1; }} }}
@keyframes slide {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes blink {{ 50% {{ opacity: 0; }} }}
@keyframes scan {{ from {{ transform: translateY(0); opacity: 1; }} 90% {{ opacity: 1; }} to {{ transform: translateY({portrait_h:.0f}px); opacity: 0; }} }}
</style>
<defs><linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{c["glyph"]}" stop-opacity="0"/><stop offset="1" stop-color="{c["glyph"]}" stop-opacity=".45"/>
</linearGradient></defs>
<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="12" fill="{c["bg"]}" stroke="{c["border"]}"/>
{portrait(grid)}
<rect class="scan" x="{PORTRAIT_X}" y="{PORTRAIT_Y - 24}" width="{len(grid[0]) * CELL_W:.0f}" height="24"/>
{info_lines(stats)}
</svg>
'''


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "assets", "portrait.json")) as f:
        grid = json.load(f)
    stats = fetch_stats()
    for theme in THEMES:
        with open(os.path.join(root, "assets", f"profile-card-{theme}.svg"), "w") as f:
            f.write(render(theme, grid, stats))


if __name__ == "__main__":
    main()
