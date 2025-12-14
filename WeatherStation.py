# ===============================
# 1. Imports
# ===============================
import subprocess
from zoneinfo import ZoneInfo
from datetime import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import requests
import json
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")  # non-interactive backend (important for Pi)


# Optional Pi-only imports
try:
    from PIL import Image
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

GRAPH_PATH = "./static/graphs/hourly_forecast_12.png"
TEMPLATE_PATH = "./templates/template.html"
OUTPUT_PATH = "./templates/output.html"


# ===============================
# 3. Load static data once
# ===============================
with open("./data/wmo_code.json") as f:
    WMO_CODE = json.load(f)


# ===============================
# 4. Plot hourly graph
# ===============================
def plot_hourly_graph(data, now):

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
        {"time": times, "hourly_temps": hourly_temps}
    ).set_index("time")

    current_hour = now.replace(minute=0, second=0, microsecond=0)

    df = df.loc[
        current_hour: current_hour + pd.Timedelta(hours=12)
    ]

    df.index = df.index.tz_localize(None)

    plt.figure(figsize=(7.8, 3))
    plt.plot(df.index, df["hourly_temps"])
    plt.fill_between(df.index, df["hourly_temps"], alpha=0.5)

    plt.gca().xaxis.set_major_formatter(
        mdates.DateFormatter("%H")
    )

    y_min = int(df["hourly_temps"].min() // 5 * 5)
    y_max = int(df["hourly_temps"].max() // 5 * 5 + 5)
    plt.yticks(np.arange(y_min, y_max + 1, 5))
    plt.yticks([])

    for x, y in zip(df.index, df["hourly_temps"]):
        plt.annotate(
            f"{y}",
            (x, y),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=16,
        )

    plt.xticks(fontsize=16)
    plt.grid(axis="y", linestyle="--", alpha=0.5)

    for spine in plt.gca().spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    plt.savefig(GRAPH_PATH, transparent=True)
    plt.close()  # IMPORTANT for headless / Pi


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
        ],
    }

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    local_tz = ZoneInfo(TZ)
    now = datetime.now(local_tz)

    plot_hourly_graph(data, now)

    is_day = "day" if data["current"]["is_day"] else "night"
    code = str(data["current"]["weather_code"])

    day_str = now.strftime("%A %B %d")
    time_str = now.strftime("%-I:%M %p").lower()

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

    print("Saved output.html")


# ===============================
# 7. Screenshot (Pi only)
# ===============================
def make_screenshot():
    subprocess.run(
        [
            "chromium-browser",
            "--headless",
            "--disable-gpu",
            "--window-size=800,480",
            "--screenshot=screen.png",
            OUTPUT_PATH,
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
    img = Image.open("screen.png")
    display.set_image(img)
    display.show()


# ===============================
# 9. Main
# ===============================
if __name__ == "__main__":
    weather = get_weather()
    render_html(weather)
    # make_screenshot()
    # show_on_inky()
