# ===============================
# 1. Imports
# ===============================
import subprocess
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import requests
import json
import pandas as pd
import numpy as np
import matplotlib
import os
from pathlib import Path


matplotlib.use("Agg")  # non-interactive backend (important for Pi)


# Optional Pi-only imports
try:
    from PIL import Image, ImageDraw
    from inky.auto import auto
except ImportError:
    Image = None
    auto = None


# ===============================
# 2. Constants / Config
# ===============================
LAT = 51.0501
LON = -114.0853
TZ = "America/Denver"


BASE_DIR = Path(__file__).resolve().parent
GRAPH_PATH = BASE_DIR / "static/graphs/hourly_forecast_12.png"
TEMPLATE_PATH = BASE_DIR / "templates/template.html"
OUTPUT_PATH = BASE_DIR / "templates/output.html"
SCREENSHOT_PATH = BASE_DIR / "screen.png"
WMO_PATH = BASE_DIR / "data/wmo_code.json"

# ===============================
# 3. Load static data once
# ===============================
with open("./data/wmo_code.json") as f:
    WMO_CODE = json.load(f)


# ===============================
# 4. Plot hourly graph
# ===============================

def plot_hourly_graph(data, now, is_day):

    hourly_temps = (
        pd.Series(data["hourly"]["temperature_2m"])
        .round()
        .astype(int)
    )

    hourly_times = data["hourly"]["time"]
    local_tz = ZoneInfo(TZ)

    times = [
        datetime.fromisoformat(t).astimezone(local_tz)
        for t in hourly_times
    ]

    df = pd.DataFrame(
        {"time": times, "hourly_temps": hourly_temps}).set_index("time")

    current_hour = now.replace(minute=0, second=0, microsecond=0)
    df = df.loc[current_hour: current_hour + pd.Timedelta(hours=12)]
    df.index = df.index.tz_localize(None)

    # =========================
    # Colors based on day/night
    # =========================
    if is_day == "day":
        line_color = "#1b1b1b"   # Soft black (less harsh than pure black)
        fill_color = "#cfae70"   # Warm sun tone
        text_color = "#1b1b1b"
        bg_color = "#fbfbf8"   # Warm off-white
    else:
        line_color = "#eaeaea"   # Soft white
        fill_color = "#7aa2c6"   # Cool moonlight blue
        text_color = "#eaeaea"
        bg_color = "#080b10"   # Deep cool night

    font_size = 16
    plt.figure(figsize=(7.8, 3), facecolor=bg_color)
    ax = plt.gca()
    ax.set_facecolor(bg_color)

    # Plot line and fill
    x = df.index
    y = df["hourly_temps"]

    padding = 1.5  # degrees of breathing room
    y_min = y.min() - padding
    y_max = y.max() + padding

    plt.plot(x, y, color=line_color, linewidth=2)
    plt.fill_between(x, y, alpha=0.25, color=fill_color)

    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-I %p"))

    plt.ylim(y_min, y_max)

    # Annotate each point
    prev = None
    for xi, yi in zip(x, y):
        alpha = 0 if yi == prev else 1.0
        prev = yi
        plt.annotate(
            f"{yi}°",
            (xi, yi),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
            fontsize=font_size,
            color=text_color,
            alpha=alpha,
        )

    plt.xticks(fontsize=font_size, color=text_color)
    ax.tick_params(axis="y", which="both", left=False, labelleft=False)
    plt.grid(axis="y", linestyle="--", alpha=0.5, color=text_color)

    # Make the line/fill touch the left/right edges of the plotting area
    ax.set_xlim(x.min(), x.max())
    ax.margins(x=0)

    # Put x tick labels "outside" by reserving bottom space manually
    # (replace tight_layout with subplots_adjust)
    plt.subplots_adjust(left=0.04, right=0.96, top=0.98, bottom=0.28)

    # Push tick labels further down (outside the plot area)
    ax.tick_params(axis="x", pad=18, colors=text_color,
                   bottom=False, labelsize=font_size)

    for spine in ax.spines.values():
        spine.set_visible(False)

    # plt.tight_layout()
    plt.savefig(GRAPH_PATH, transparent=True)
    plt.close()


# ===============================
# 5. Fetch weather data
# ===============================
def get_weather():

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TZ,
        "models": "best_match",
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "is_day",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "weather_code",
        ],
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation_probability",
            "wind_speed_10m",
            "weather_code",
        ],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "weather_code",
        ],
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    if "current" not in data or "hourly" not in data:
        raise RuntimeError(f"Unexpected API response: {data.keys()}")

    # print(data)

    local_tz = ZoneInfo(TZ)
    now = datetime.now(local_tz)

    is_day = "day" if data["current"]["is_day"] else "night"
    code = str(data["current"]["weather_code"])

    day_str = now.strftime("%A %B %d")
    time_str = now.strftime("%-I:%M %p").lower()

    plot_hourly_graph(data, now, is_day)

    week = []
    for i in range(1, 7):  # next 6 days (tomorrow..6 days out)
        dt = now + timedelta(days=i)

        week.append({
            "DOW": dt.strftime("%a"),  # Mon, Tue...
            "HIGH": round(data["daily"]["temperature_2m_max"][i]),
            "LOW": round(data["daily"]["temperature_2m_min"][i]),
            "ICON": WMO_CODE[str(data["daily"]["weather_code"][i])]["day"]["icon"],
        })

    def build_week_cards_html(week):
        parts = []
        for d in week:
            parts.append(
                f"""
                <div class="day-card">
                <div class="dow">{d["DOW"]}</div>
                <img class="day-icon" src="../static/icons/{d["ICON"]}" alt="" />
                <div class="temps">
                    <span class="high">{d["HIGH"]}°</span>
                    <span class="low">{d["LOW"]}°</span>
                </div>
                </div>
                """.strip()
            )
        return "\n".join(parts)

    week_cards_html = build_week_cards_html(week)

    return {
        "TEMP": round(data["current"]["temperature_2m"]),
        "FEELS": round(data["current"]["apparent_temperature"]),
        "HUMIDITY": data["current"]["relative_humidity_2m"],
        "WIND": data["current"]["wind_speed_10m"],
        "DESC": WMO_CODE[code][is_day]["description"],
        "CURRENT_ICON": WMO_CODE[code][is_day]["icon"],
        "PRECIP%": data["daily"]["precipitation_probability_max"][0],
        "TIME": f"Last updated: {time_str}",
        "DAY": day_str,
        "HIGH": round(data["daily"]["temperature_2m_max"][0]),
        "LOW": round(data["daily"]["temperature_2m_min"][0]),
        "MODE": is_day,
        "WEEK_CARDS": week_cards_html,
    }


# ===============================
# 6. Render HTML
# ===============================
def render_html(weather):

    with open(TEMPLATE_PATH, "r") as f:
        html = f.read()

    for key, value in weather.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))

    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    # print("Saved output.html")


# ===============================
# 7. Screenshot (Pi only)
# ===============================

# def make_screenshot():
#     html_path = OUTPUT_PATH.resolve()
#     subprocess.run(
#         [
#             "chromium-browser",
#             "--headless",
#             "--disable-gpu",
#             "--window-size=800,480",
#             f"--screenshot={SCREENSHOT_PATH}",
#             f"file://{html_path}",
#         ],
#         check=True,
#     )


def make_screenshot():
    html_path = OUTPUT_PATH.resolve()
    screenshot_path = SCREENSHOT_PATH.resolve()

    subprocess.run(
        [
            "wkhtmltoimage",
            "--width", "800",
            "--height", "480",
            "--disable-smart-width",
            "--quality", "100",
            "--format", "png",
            f"file://{html_path}",
            str(screenshot_path),
        ],
        check=True,
    )


# ===============================
# 8. Display on Inky (Pi only)
# ===============================
def show_on_inky():
    if auto is None or Image is None:
        return

    display = auto()
    w, h = display.resolution

    img = Image.open(SCREENSHOT_PATH).convert("RGB")
    if img.size != (w, h):
        img = img.resize((w, h), Image.Resampling.LANCZOS)

    display.set_image(img)
    display.show()


# ===============================
# 9. Main
# ===============================
if __name__ == "__main__":
    print("Fetching weather...")
    data = get_weather()

    print("Rendering HTML...")
    render_html(data)

    print("Taking screenshot...")
    make_screenshot()

    print("Showing on Inky...")
    show_on_inky()

    print("Done.")
