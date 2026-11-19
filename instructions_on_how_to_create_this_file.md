## **1. Create a Repository**

1. Visit GitHub – New Repository.
2. Name the repository after your GitHub username.

For example, if your username is `trantuandev`, name the repository `trantuandev`.\
3\. Select **Public**.\
4\. Check **Add a README file**.\
5\. Click **Create repository**.

## **2. Create a Workflow to Generate contributions.svg**

To automatically update the snake image based on GitHub activity, use GitHub Actions with the Platane/snk library.

In your repository, create this directory and file:

```
trantuandev/
└── .github/
    └── workflows/
        └── contributions.yml
```

Paste the following into `contributions.yml`:

```

name: Generate Contributions Snake

on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  generate:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate snake
        uses: Platane/snk/svg-only@v3
        with:
          github_user_name: trantuandev
          outputs: dist/contributions.svg

      - name: Copy SVG
        run: cp dist/contributions.svg contributions.svg

      - name: Commit SVG
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: Update contributions.svg

```

**Note:** Replace `trantuandev` with your GitHub username if it is different.

This workflow creates `contributions.svg` on the `main` branch and updates it daily.

## **3. Allow GitHub Actions to Write Files**

In your repository:

1. Select **Settings**.
2. Select **Actions → General**.
3. Find **Workflow permissions**.
4. Select **Read and write permissions**.
5. Click **Save**.

## **4. Test the Workflow**

1. Select the **Actions** tab.
2. Select the **Generate Contributions Snake** workflow.
3. Click **Run workflow**.
4. Wait for the workflow to succeed (a green check mark).

You will then have this URL: https://raw.githubusercontent.com/trantuandev/trantuandev/main/contributions.svg


## **5. Display It in Your GitHub Profile README**

Add this snippet to your `README.md`:

```
<img src="https://raw.githubusercontent.com/trantuandev/trantuandev/main/contributions.svg" alt="GitHub Contributions Snake" />
```


## **1. Project Structure After Setup**

Add the following files to your repository:

```
trantuandev/
│
├── .github/
│   └── workflows/
│       └── contributions.yml
│
├── scripts/
│   └── generate_dashboard.py
│
├── dashboard.svg
├── contributions.svg
└── README.md
```

- `generate_dashboard.py`: fetches data and renders the dashboard.
- `dashboard.svg`: a GitHub + GitLab statistics dashboard.
- `contributions.svg`: the Contribution Snake image, if you want to keep it.
- `contributions.yml`: updates the snake image daily.

## **2. Prepare Your GitHub and GitLab Accounts**

To retrieve the data, you need to create two access tokens.

### **2.1. Create a GitHub Token**

Visit GitHub Personal Access Tokens.

1. Select **Tokens (classic)**.
2. Click **Generate new token (classic)**.
3. Name it `contribution-dashboard`.
4. Choose an appropriate expiration period.
5. Select the `read:user` permission.
6. Click **Generate token**.
7. Copy the token and store it securely.


### **2.2. Create a GitLab Token**

Visit:

GitLab Personal Access Tokens
1. Name it `contribution-dashboard`.
2. Select the `read_user` permission.
3. Create the token.
4. Copy and store it securely.

GitLab uses the `read_user` permission to query user activity through the Events API.

**Security:** Do not paste either token into the Python code, README, or YAML files. Store them as GitHub Secrets instead.


## **3. Add GitHub Secrets**

Open the repository:

[trantuandev – Actions secrets]

Select **New repository secret** and create these two secrets:

| Name       | Value                |
| ---------- | -------------------- |
| `GH_TOKEN` | The GitHub token you created |
| `GL_TOKEN` | The GitLab token you created |

Click **Save secret** for each token.

## **4. Create the Python File**

In the repository, create a `scripts` directory, then add this file:

```
scripts/generate_dashboard.py
```

This script will:

- Fetch the GitHub contribution calendar for the last 365 days.
- Fetch GitLab events for the same period.
- Combine activity by date.
- Calculate Total Activity, Active Days, Current Streak, and Best Day.
- Export a dark-themed SVG.

Paste the complete code below into `generate_dashboard.py`:

```

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

GITHUB_USERNAME = "trantuandev"
GITLAB_USERNAME = os.environ.get("GITLAB_USERNAME", "YOUR_GITLAB_USERNAME")

GH_TOKEN = os.environ["GH_TOKEN"]
GL_TOKEN = os.environ["GL_TOKEN"]

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

    variables = {
        "login": GITHUB_USERNAME,
        "from": datetime.combine(
            START_DATE, datetime.min.time(), timezone.utc
        ).isoformat(),
        "to": datetime.now(timezone.utc).isoformat()
    }

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
# GITLAB EVENTS
# ==========================================

def get_gitlab_data():
    print("Fetching GitLab events...")

    if not GITLAB_USERNAME or GITLAB_USERNAME == "YOUR_GITLAB_USERNAME":
        raise RuntimeError(
            "Please set your actual GitLab username."
        )

    username = urllib.parse.quote(GITLAB_USERNAME, safe="")

    base_url = (
        f"https://gitlab.com/api/v4/users/"
        f"{username}/events"
    )

    params = {
        "after": START_DATE.isoformat(),
        "before": TODAY.isoformat(),
        "per_page": 100,
        "page": 1,
        "sort": "asc"
    }

    daily = defaultdict(int)
    total = 0

    while True:
        url = base_url + "?" + urllib.parse.urlencode(params)

        events, headers = request_json(
            url,
            headers={
                "PRIVATE-TOKEN": GL_TOKEN,
                "User-Agent": "Contribution-Dashboard"
            }
        )

        if not events:
            break

        for event in events:
            event_date = datetime.fromisoformat(
                event["created_at"].replace("Z", "+00:00")
            ).date()

            if START_DATE <= event_date <= TODAY:
                daily[event_date] += 1
                total += 1

        next_page = headers.get("X-Next-Page")

        if not next_page:
            break

        params["page"] = int(next_page)

    print("GitLab total events:", total)

    return dict(daily), total


# ==========================================
# MERGE DATA
# ==========================================

github_daily, github_total = get_github_data()
gitlab_daily, gitlab_total = get_gitlab_data()

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

```

**Calculation note:** Total Activity is the sum of the GitHub contributions and GitLab events returned by the APIs. GitLab events are not exactly equivalent to GitHub's contribution calendar; this API may not return some activity types, such as merge requests.


## **5. Create a GitHub Actions Workflow to Update the Dashboard**

Create a new file:

```
.github/workflows/dashboard.yml
```

Paste in this configuration:

```

name: Update Contribution Dashboard

on:
  schedule:
    - cron: "0 0 * * *"

  workflow_dispatch:

permissions:
  contents: write

jobs:
  generate-dashboard:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Generate dashboard
        env:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          GL_TOKEN: ${{ secrets.GL_TOKEN }}
          GITLAB_USERNAME: YOUR_GITLAB_USERNAME
        run: python scripts/generate_dashboard.py

      - name: Commit dashboard
        uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "Update contribution dashboard"
          file_pattern: dashboard.svg

```

**Important:** Replace `YOUR_GITLAB_USERNAME` with your actual GitLab username.

After you save the file, the workflow will run daily at 00:00 UTC (07:00 Vietnam time). You can also run it manually from the Actions tab.

## **6. Display the Dashboard on Your GitHub Profile**

Open `README.md` in the `trantuandev/trantuandev` repository.

Add the following snippet wherever you want the dashboard to appear:

```

<h2 align="center">📊 My Contribution Dashboard</h2>

<p align="center">
  <img
    src="https://raw.githubusercontent.com/trantuandev/trantuandev/main/dashboard.svg"
    alt="Contribution Dashboard"
    width="100%"
  />
</p>

```

Click **Commit changes** to save.

After the workflow succeeds, you can open the dashboard here: https://github.com/trantuandev/trantuandev/blob/main/dashboard.svg?utm_source=chatgpt.com

## **7. Test the Dashboard**

After creating all the files, follow these steps:

1. Commit `generate_dashboard.py`.
2. Commit `dashboard.yml`.
3. Open the **Actions** tab.
4. Select **Update Contribution Dashboard** from the left-hand menu.
5. Click **Run workflow**.
6. Wait for the workflow to finish.