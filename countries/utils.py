import requests
from django.utils import timezone
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import os

COUNTRIES_API = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
RATES_API = "https://open.er-api.com/v6/latest/USD"
REQUEST_TIMEOUT = 10  # seconds

def fetch_countries():
    resp = requests.get(COUNTRIES_API, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def fetch_rates():
    resp = requests.get(RATES_API, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    # API has structure { "result": "success", "rates": { "USD":1, "NGN":... }, ... }
    rates = data.get("rates") or {}
    return rates

def compute_estimated_gdp(population, exchange_rate):
    # If exchange_rate is None or zero, return None (per spec if rate missing -> estimated_gdp null)
    if exchange_rate in (None, 0):
        return None
    multiplier = random.uniform(1000, 2000)
    return (population * multiplier) / exchange_rate

def generate_summary_image(total_countries, top_five, timestamp, out_path):
    """
    top_five: list of tuples (name, estimated_gdp) sorted desc
    Save to out_path (path to cache/summary.png)
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    width, height = 1200, 675
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to pick a common font; fallback to default
    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_text = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_text = ImageFont.load_default()

    x = 40
    y = 40
    draw.text((x, y), "Countries Summary", font=font_title, fill=(0,0,0))
    y += 60
    draw.text((x, y), f"Total countries: {total_countries}", font=font_text, fill=(0,0,0))
    y += 30
    draw.text((x, y), f"Last refresh: {timestamp.isoformat()}", font=font_text, fill=(0,0,0))
    y += 40
    draw.text((x, y), "Top 5 countries by estimated GDP:", font=font_text, fill=(0,0,0))
    y += 30
    for i, (name, gdp) in enumerate(top_five, start=1):
        gdp_str = "N/A" if gdp is None else f"{gdp:,.2f}"
        draw.text((x, y), f"{i}. {name} — {gdp_str}", font=font_text, fill=(0,0,0))
        y += 26

    img.save(out_path)
    return out_path
