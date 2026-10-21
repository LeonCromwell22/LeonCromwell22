"""Draw the last 30 days of GitHub contributions as an animated SVG.

Usage: activity_graph.py <login> <output.svg>   (token read from GH_TOKEN)
Only daily counts are used; no repository names reach the output.
"""
import json
import os
import sys
import urllib.request
from datetime import date

DAYS = 30
W, H = 1000, 300
L, R, T, B = 64, 36, 70, 56  # plot margins

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "activity-graph"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    return days[-DAYS:]


def smooth_path(pts, y_min, y_max):
    """Catmull-Rom to cubic Bezier, control points clamped so the line never dips below zero."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(max(p1[1] + (p2[1] - p0[1]) / 6, y_min), y_max))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(max(p2[1] - (p3[1] - p1[1]) / 6, y_min), y_max))
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def nice_max(v):
    for step in (4, 8, 12, 20, 40, 80, 160, 400):
        if v <= step:
            return step
    return int(v) + 1


def render(days):
    counts = [d["contributionCount"] for d in days]
    total = sum(counts)
    ymax = nice_max(max(counts) if counts else 1)
    pw, ph = W - L - R, H - T - B
    n = len(counts)
    xs = [L + pw * i / (n - 1) for i in range(n)]
    ys = [T + ph * (1 - c / ymax) for c in counts]
    pts = list(zip(xs, ys))
    line = smooth_path(pts, T, T + ph)
    area = f"{line} L{xs[-1]:.1f},{T + ph} L{xs[0]:.1f},{T + ph} Z"

    grid = ""
    for k in range(5):
        gy = T + ph * k / 4
        label = round(ymax * (1 - k / 4))
        grid += (f'<line x1="{L}" y1="{gy:.1f}" x2="{W - R}" y2="{gy:.1f}" class="grid"/>'
                 f'<text x="{L - 12}" y="{gy + 4:.1f}" class="axis" text-anchor="end">{label}</text>')

    labels = ""
    for i in range(0, n, 5):
        dt = date.fromisoformat(days[i]["date"])
        labels += f'<text x="{xs[i]:.1f}" y="{T + ph + 26}" class="axis" text-anchor="middle">{dt.strftime("%b")} {dt.day}</text>'

    dots = ""
    for i, (x, y) in enumerate(pts):
        if counts[i] > 0:
            dots += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" class="dot" '
                     f'style="animation-delay:{1.2 + i * 0.04:.2f}s"/>')

    start = date.fromisoformat(days[0]["date"]).strftime("%b %d").replace(" 0", " ")
    end = date.fromisoformat(days[-1]["date"]).strftime("%b %d").replace(" 0", " ")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Contribution activity, {start} to {end}: {total} contributions">
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#818cf8" stop-opacity=".45"/>
      <stop offset="1" stop-color="#818cf8" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="stroke" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38bdf8"/><stop offset="1" stop-color="#c084fc"/>
    </linearGradient>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#1a1236"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: 'Segoe UI', 'Helvetica Neue', Arial, system-ui, sans-serif; }}
    .title {{ fill: #e2e8f0; font-size: 20px; font-weight: 600; }}
    .sub   {{ fill: #94a3b8; font-size: 13px; letter-spacing: 1px; }}
    .axis  {{ fill: #94a3b8; font-size: 12px; }}
    .grid  {{ stroke: #94a3b8; stroke-opacity: .12; stroke-dasharray: 3 5; }}
    .line  {{ fill: none; stroke: url(#stroke); stroke-width: 3; stroke-linecap: round; stroke-linejoin: round;
              stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 1.8s ease-out .2s forwards; }}
    .area  {{ fill: url(#fill); opacity: 0; animation: show 1s ease-out 1.2s forwards; }}
    .dot   {{ fill: #e0e7ff; stroke: #818cf8; stroke-width: 2; opacity: 0; animation: pop .5s ease-out forwards; }}
    @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
    @keyframes show {{ to {{ opacity: 1; }} }}
    @keyframes pop  {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  </style>
  <rect width="{W}" height="{H}" rx="18" fill="url(#bg)"/>
  <rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18" fill="none" stroke="#6366f1" stroke-opacity=".35"/>
  <text x="{L}" y="38" class="title">Contribution activity</text>
  <text x="{W - R}" y="38" class="sub" text-anchor="end">{start} - {end}  &#183;  {total} CONTRIBUTIONS</text>
  {grid}
  {labels}
  <path d="{area}" class="area"/>
  <path d="{line}" class="line" pathLength="1"/>
  {dots}
</svg>
'''


def main():
    login, out = sys.argv[1], sys.argv[2]
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN is not set")
    svg = render(fetch(login, token))
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
