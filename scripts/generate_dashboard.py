
import os
import json
import urllib.request
import datetime
from collections import defaultdict
from xml.sax.saxutils import escape

# ==========================================
# CONFIGURATION
# ==========================================

GITHUB_USERNAME = "trantuandev"
GH_TOKEN = os.environ["GH_TOKEN"]

TODAY = datetime.date.today()
START_DATE = TODAY - datetime.timedelta(days=364)

WIDTH = 1000
HEIGHT = 465

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


# ==========================================
# GITHUB API
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

    start = datetime.datetime.combine(
        START_DATE,
        datetime.time.min,
        datetime.timezone.utc
    )

    end = datetime.datetime.now(datetime.timezone.utc)

    variables = {
        "login": GITHUB_USERNAME,
        "from": start.isoformat(),
        "to": end.isoformat()
    }

    payload = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "GitHub-Contribution-Dashboard"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

    except Exception as error:
        raise RuntimeError(
            f"Unable to connect to GitHub API: {error}"
        ) from error

    if result.get("errors"):
        raise RuntimeError(
            f"GitHub GraphQL error: {result['errors']}"
        )

    user = result.get("data", {}).get("user")

    if not user:
        raise RuntimeError(
            f"GitHub user not found: {GITHUB_USERNAME}"
        )

    calendar = user["contributionsCollection"][
        "contributionCalendar"
    ]

    daily = {}

    for week in calendar["weeks"]:
        for item in week["contributionDays"]:
            day = datetime.date.fromisoformat(item["date"])
            daily[day] = item["contributionCount"]

    print("GitHub contributions:", calendar["totalContributions"])

    return daily, calendar["totalContributions"]


# ==========================================
# CALCULATE STATISTICS
# ==========================================

def calculate_statistics(daily):
    total_activity = sum(daily.values())

    active_days = sum(
        1 for count in daily.values() if count > 0
    )

    best_day = max(daily.values(), default=0)

    # Current streak
    streak = 0

    check_day = (
        TODAY
        if daily.get(TODAY, 0) > 0
        else TODAY - datetime.timedelta(days=1)
    )

    while daily.get(check_day, 0) > 0:
        streak += 1
        check_day -= datetime.timedelta(days=1)

    return total_activity, active_days, streak, best_day


# ==========================================
# SVG HELPERS
# ==========================================

def svg_text(x, y, content, size=12, color=TEXT, weight="normal"):
    return (
        f'<text x="{x}" y="{y}" '
        f'font-size="{size}" fill="{color}" '
        f'font-weight="{weight}">'
        f'{escape(str(content))}</text>'
    )


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


# ==========================================
# GENERATE DASHBOARD SVG
# ==========================================

def generate_dashboard(daily, total, active, streak, best):
    print("Generating dashboard.svg...")

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">',

        f'<rect width="100%" height="100%" '
        f'rx="12" fill="{BACKGROUND}"/>'
    ]

    # Header
    svg.append(
        svg_text(
            25, 42,
            "CONTRIBUTION DASHBOARD",
            25, TEXT, "bold"
        )
    )

    svg.append(
        svg_text(
            25, 69,
            f"{GITHUB_USERNAME} - GitHub",
            13, MUTED
        )
    )

    svg.append(
        svg_text(
            25, 100,
            f"{START_DATE.strftime('%d %b %Y')} - "
            f"{TODAY.strftime('%d %b %Y')}",
            13, MUTED
        )
    )

    # Statistics cards
    stats = [
        ("TOTAL ACTIVITY", total, "#39d353"),
        ("ACTIVE DAYS", active, "#26a641"),
        ("CURRENT STREAK", streak, "#58a6ff"),
        ("BEST DAY", best, "#d2a8ff")
    ]

    card_width = 225
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

        svg.append(
            svg_text(
                x + 15, card_y + 30,
                label, 11, MUTED
            )
        )

        svg.append(
            svg_text(
                x + 15, card_y + 68,
                value, 29, color, "bold"
            )
        )

    # Heatmap
    svg.append(
        svg_text(
            25, 230,
            "DAILY ACTIVITY",
            13, TEXT, "bold"
        )
    )

    CELL = 13
    GAP = 4
    STEP = CELL + GAP

    LEFT = 42
    TOP = 245

    # Sunday as first column in each week
    grid_start = START_DATE - datetime.timedelta(
        days=(START_DATE.weekday() + 1) % 7
    )

    weeks = (
        (TODAY - grid_start).days // 7
    ) + 1

    maximum = max(daily.values(), default=1)

    # Month labels
    previous_month = None

    for week in range(weeks):
        current_date = grid_start + datetime.timedelta(
            days=week * 7
        )

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
    for row, label in [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]:
        svg.append(
            svg_text(
                0,
                TOP + row * STEP + 10,
                label,
                11,
                MUTED
            )
        )

    # Daily contribution squares
    for week in range(weeks):
        for weekday in range(7):
            current_date = grid_start + datetime.timedelta(
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
                f'<title>{current_date}: '
                f'{value} contributions</title>'
                f'</rect>'
            )

    # Legend
    legend_y = TOP + 7 * STEP + 28

    svg.append(
        svg_text(25, legend_y, "Less", 11, MUTED)
    )

    for index, color in enumerate(COLORS):
        x = 75 + index * 20

        svg.append(
            f'<rect x="{x}" y="{legend_y - 13}" '
            f'width="14" height="14" '
            f'rx="3" fill="{color}"/>'
        )

    svg.append(
        svg_text(185, legend_y, "More", 11, MUTED)
    )

    # Footer
    svg.append(
        svg_text(
            25, HEIGHT - 16,
            f"GitHub: {total} contributions | "
            f"Updated automatically with GitHub Actions",
            11, MUTED
        )
    )

    svg.append("</svg>")

    with open(
        "dashboard.svg",
        "w",
        encoding="utf-8"
    ) as file:
        file.write("\n".join(svg))

    print("Dashboard generated successfully!")


# ==========================================
# MAIN
# ==========================================

def main():
    daily, github_total = get_github_data()

    # Fill missing dates with zero
    for offset in range(365):
        day = START_DATE + datetime.timedelta(days=offset)
        daily.setdefault(day, 0)

    total, active, streak, best = calculate_statistics(daily)

    generate_dashboard(
        daily,
        total,
        active,
        streak,
        best
    )

    print("--------------------------------")
    print("GitHub username:", GITHUB_USERNAME)
    print("Total activity:", total)
    print("Active days:", active)
    print("Current streak:", streak)
    print("Best day:", best)
    print("--------------------------------")


if __name__ == "__main__":
    main()
