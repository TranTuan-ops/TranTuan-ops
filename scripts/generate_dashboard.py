
import os
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict
from xml.sax.saxutils import escape

# ==========================================
# CONFIGURATION
# ==========================================

GITHUB_USERNAME = "TranTuan-ops"

GH_TOKEN = os.environ["GH_TOKEN"]

TODAY = date.today()
START_DATE = TODAY - timedelta(days=364)

# ==========================================
# HTTP HELPER
# ==========================================

def request_json(url, method="GET", headers=None, data=None):
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers or {},
        method=method
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")), response.headers
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"API error {e.code}: {detail[:1000]}"
        ) from e


# ==========================================
# GITHUB CONTRIBUTIONS
# ==========================================

def get_github_data():
    print("Fetching GitHub contributions...")

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    payload = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    result, _ = request_json(
        "https://api.github.com/graphql",
        method="POST",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Contribution-Dashboard"
        },
        data=payload
    )

    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL: {result['errors']}")

    user = result["data"]["user"]

    if not user:
        raise RuntimeError("GitHub username not found.")

    calendar = user["contributionsCollection"]["contributionCalendar"]

    daily = {}

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            daily[date.fromisoformat(day["date"])] = (
                day["contributionCount"]
            )

    print("GitHub total:", calendar["totalContributions"])

    return daily, calendar["totalContributions"]

# ==========================================
# MERGE DATA
# ==========================================

github_daily, github_total = get_github_data()

daily = defaultdict(int)

for day, count in github_daily.items():
    daily[day] += count

for day, count in gitlab_daily.items():
    daily[day] += count

for offset in range(365):
    day = START_DATE + timedelta(days=offset)
    daily.setdefault(day, 0)

total_activity = sum(daily.values())

active_days = sum(
    1 for count in daily.values() if count > 0
)

best_day = max(daily.values(), default=0)

# Current streak: if today has no activity,
# continue checking from yesterday.
streak = 0
check_day = TODAY if daily[TODAY] > 0 else TODAY - timedelta(days=1)

while daily.get(check_day, 0) > 0:
    streak += 1
    check_day -= timedelta(days=1)


# ==========================================
# SVG CONFIGURATION
# ==========================================

WIDTH = 1100
HEIGHT = 465

LEFT = 42
TOP = 195

CELL = 13
GAP = 4
STEP = CELL + GAP

BACKGROUND = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"

COLORS = [
    "#21262d",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353"
]

def get_color(value, maximum):
    if value == 0:
        return COLORS[0]

    ratio = value / max(maximum, 1)

    if ratio <= 0.25:
        return COLORS[1]
    elif ratio <= 0.50:
        return COLORS[2]
    elif ratio <= 0.75:
        return COLORS[3]

    return COLORS[4]


def svg_text(x, y, content, size=12, color=TEXT, weight="normal"):
    return (
        f'<text x="{x}" y="{y}" '
        f'font-size="{size}" fill="{color}" '
        f'font-weight="{weight}">{escape(str(content))}</text>'
    )


# ==========================================
# BUILD SVG
# ==========================================

svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{WIDTH}" height="{HEIGHT}" '
    f'viewBox="0 0 {WIDTH} {HEIGHT}">',
    f'<rect width="100%" height="100%" rx="12" fill="{BACKGROUND}"/>'
]

# Header

svg.append(
    svg_text(25, 42, "CONTRIBUTION DASHBOARD", 25, TEXT, "bold")
)

svg.append(
    svg_text(
        25, 69,
        f"{GITHUB_USERNAME} + GitLab / {GITLAB_USERNAME}",
        13, MUTED
    )
)

svg.append(
    svg_text(
        25, 100,
        f"{START_DATE.strftime('%d %b %Y')} — "
        f"{TODAY.strftime('%d %b %Y')}",
        13, MUTED
    )
)

# Statistics cards

stats = [
    ("TOTAL ACTIVITY", total_activity, "#39d353"),
    ("ACTIVE DAYS", active_days, "#26a641"),
    ("CURRENT STREAK", streak, "#58a6ff"),
    ("BEST DAY", best_day, "#d2a8ff")
]

card_width = 256
card_height = 95
card_gap = 15
card_y = 118

for index, (label, value, color) in enumerate(stats):
    x = 25 + index * (card_width + card_gap)

    svg.append(
        f'<rect x="{x}" y="{card_y}" '
        f'width="{card_width}" height="{card_height}" '
        f'rx="12" fill="{CARD}" stroke="{BORDER}"/>'
    )

    svg.append(svg_text(x + 15, card_y + 30, label, 11, MUTED))
    svg.append(
        svg_text(x + 15, card_y + 68, value, 29, color, "bold")
    )

# Heatmap

svg.append(
    svg_text(25, 230, "DAILY ACTIVITY", 13, TEXT, "bold")
)

grid_start = START_DATE - timedelta(
    days=(START_DATE.weekday() + 1) % 7
)

weeks = ((TODAY - grid_start).days // 7) + 1

maximum = max(daily.values(), default=1)

# Month labels

previous_month = None

for week in range(weeks):
    current_date = grid_start + timedelta(days=week * 7)

    if current_date.month != previous_month:
        x = LEFT + week * STEP

        svg.append(
            svg_text(
                x, TOP - 12,
                current_date.strftime("%b"),
                11, MUTED
            )
        )

        previous_month = current_date.month

# Weekday labels

for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
    svg.append(
        svg_text(
            0, TOP + row * STEP + 10,
            label, 11, MUTED
        )
    )

# Daily squares

for week in range(weeks):
    for weekday in range(7):
        current_date = grid_start + timedelta(
            days=week * 7 + weekday
        )

        if current_date < START_DATE or current_date > TODAY:
            continue

        value = daily.get(current_date, 0)

        x = LEFT + week * STEP
        y = TOP + weekday * STEP

        color = get_color(value, maximum)

        svg.append(
            f'<rect x="{x}" y="{y}" '
            f'width="{CELL}" height="{CELL}" '
            f'rx="3" fill="{color}">'
            f'<title>{current_date}: {value} activities</title>'
            f'</rect>'
        )

# Legend

legend_y = TOP + 7 * STEP + 28

svg.append(svg_text(25, legend_y, "Less", 11, MUTED))

for i, color in enumerate(COLORS):
    x = 75 + i * 20

    svg.append(
        f'<rect x="{x}" y="{legend_y - 13}" '
        f'width="14" height="14" rx="3" fill="{color}"/>'
    )

svg.append(svg_text(185, legend_y, "More", 11, MUTED))

# Footer

footer_y = HEIGHT - 16

svg.append(
    svg_text(
        25, footer_y,
        f"GitHub: {github_total} contributions | "
        f"GitLab: {gitlab_total} events | "
        f"Updated automatically with GitHub Actions",
        11, MUTED
    )
)

svg.append("</svg>")

# Save SVG

with open("dashboard.svg", "w", encoding="utf-8") as file:
    file.write("\n".join(svg))

print("Dashboard generated successfully!")
print("Total activity:", total_activity)
print("Active days:", active_days)
print("Current streak:", streak)
print("Best day:", best_day)
