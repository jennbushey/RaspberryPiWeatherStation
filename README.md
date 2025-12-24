Got it — thanks for the correction 👍
Here’s a **revised README** that accurately reflects your setup using **HTML/CSS + `wkhtmltoimage`**, _not_ Pillow.

You can replace the previous one entirely with this.

---

# Raspberry Pi Weather Station (Inky Impressions 7.3")

A headless weather display built on a **Raspberry Pi** and **Pimoroni Inky Impressions 7.3" e-ink display**.
The station fetches weather data from **Open-Meteo**, renders a static **HTML/CSS weather dashboard**, converts it to an image using **`wkhtmltoimage`**, and displays it on the e-ink panel.

The design prioritizes:

-   Reliability on low-power hardware (Pi Zero compatible)
-   Clear, high-contrast e-ink visuals
-   Simple recovery if the SD card needs to be rebuilt
-   Separation of layout (HTML/CSS) from data (Python)

---

## Features

-   **Current conditions**

    -   Temperature, “feels like”, high / low
    -   Weather description and icon
    -   Last updated time

-   **Hourly temperature graph**

    -   Next 12 hours
    -   Rendered with Matplotlib
    -   Optimized spacing and labels for e-ink

-   **6-day forecast**

    -   Day of week
    -   Weather icon
    -   High / low temperatures

-   **Day / night modes**

    -   Warm daytime palette
    -   Cool nighttime palette

-   **Static rendering pipeline**

    -   No live browser
    -   No JavaScript required at runtime

---

## Hardware

-   Raspberry Pi (tested with Raspberry Pi Zero)
-   Pimoroni **Inky Impressions 7.3"**
-   MicroSD card running Raspberry Pi OS

---

## Software Stack

-   Python 3
-   `requests` – Open-Meteo API calls
-   `matplotlib` – hourly temperature graph
-   `pandas` / `numpy` – data processing
-   **HTML + CSS** – layout and styling
-   **`wkhtmltoimage`** – convert HTML → PNG
-   `inky` – display driver

---

## Data Source

Weather data is provided by **Open-Meteo**:

-   Free and open (no API key required)
-   Hourly and daily forecasts
-   Timezone support

Open-Meteo API
[https://open-meteo.com/](https://open-meteo.com/)

---

## Display Driver

The e-ink display is driven using Pimoroni’s official **Inky** Python library.

Pimoroni Inky GitHub
[https://github.com/pimoroni/inky](https://github.com/pimoroni/inky)

---

## How It Works (Pipeline)

1. **Fetch weather data**

    - Open-Meteo API
    - Timezone explicitly set (`America/Denver`)

2. **Process data**

    - Extract current, hourly, and daily values
    - Build a 6-day forecast (excluding today)

3. **Generate hourly graph**

    - Matplotlib outputs a transparent PNG

4. **Render HTML**

    - Python replaces placeholders in an HTML template
    - CSS handles all layout and theming

5. **Convert HTML → image**

    - `wkhtmltoimage` renders the page at 800×480

6. **Display on e-ink**

    - Image is sent to the Inky display

---

## Timezone Handling (Important)

Open-Meteo returns hourly timestamps **without an explicit UTC offset**, but already localized to the requested timezone.

To avoid double-shifting:

-   Hourly timestamps are **assigned** the local timezone (`replace(tzinfo=...)`)
-   They are **not converted** from UTC

This ensures:

-   “Now” aligns with the left edge of the hourly graph
-   No off-by-one-hour errors

---

## Project Structure

```
RaspberryPiWeatherStation/
│
├── WeatherStation.py
├── screen.png
│
├── templates/
│   ├── template.html
│   └── output.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── graphs/
│   │   └── hourly_forecast_12.png
│   └── icons/
│
├── data/
│   └── wmo_code.json
│
└── README.md
```

---

## Running the Project

Activate your environment (if applicable):

```bash
source ~/.virtualenvs/inky/bin/activate
```

Run the script:

```bash
python WeatherStation.py
```

---

## Scheduling Updates

Recommended update interval: **every 15 minutes**

Options:

-   `cron` (simple)
-   `systemd` service + timer (more robust)

Frequent updates should be balanced against:

-   E-ink refresh time
-   Display wear

---

## E-Ink Design Notes

-   High-contrast colors only
-   Minimal gradients
-   Large, readable typography
-   Static layout (no animation)
-   Avoid unnecessary refreshes

---

## Future Improvements

-   Sunrise / sunset indicators
-   Wind direction visualization
-   Indoor sensor data
-   Power-saving sleep between updates
-   Manual refresh button
