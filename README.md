# Find My Home 🏠

Find rentals in Botswana fast — scrapes Facebook Search and Marketplace so you don't have to scroll through dozens of groups manually.


## Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![Claude AI](https://img.shields.io/badge/Claude_AI-D4A820?style=for-the-badge&logo=anthropic&logoColor=black)
![Facebook](https://img.shields.io/badge/Facebook_Scraper-1877F2?style=for-the-badge&logo=facebook&logoColor=white)

| Tool | Purpose |
|---|---|
| **Python** | Core runtime |
| **Playwright** | Headless browser automation for Facebook scraping |
| **Claude AI (Haiku)** | Parses informal rental posts into structured JSON |
| **Chromium** | Browser engine via Playwright |

## What it does

- Searches Facebook posts across all groups, pages, and profiles for houses, flats, and rooms for rent in Botswana
- Also scrapes Facebook Marketplace for Botswana cities
- Uses Claude AI (Haiku) to parse messy informal posts into clean, structured data
- Outputs: price (BWP), bedrooms, location, contact number, amenities


## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

Get a key at [console.anthropic.com](https://console.anthropic.com) (~$0.03 per 100 posts).

### 3. Log into Facebook once

```bash
python main.py login
```

A browser window opens — log in manually, then press Enter. Your session is saved to `auth_state.json` (never committed to git).

## Usage

```bash
# Search Facebook posts for rentals (all preset Botswana queries)
python main.py search --output listings.json

# Custom search query
python main.py search --query "2 bedroom flat Gaborone" --output listings.json

# Scrape Facebook Marketplace
python main.py marketplace --city Gaborone --output listings.json

# Run everything — search + marketplace for all cities
python main.py all --output listings.json

# See the browser while it runs
python main.py search --show
```

## Output format

Each listing looks like:

```json
{
  "listing_type": "house",
  "bedrooms": 3,
  "bathrooms": 2,
  "price_bwp": 6500,
  "price_period": "monthly",
  "location": "Phakalane, Gaborone",
  "amenities": ["borehole water", "garage", "large yard"],
  "contact_phone": "71234567",
  "contact_name": "Thabo",
  "furnished": false,
  "available_from": "immediately",
  "summary": "3-bedroom house in Phakalane, P6500/month, borehole water and garage.",
  "link": "https://www.facebook.com/...",
  "image": "https://scontent..."
}
```

## Botswana cities covered

Gaborone, Francistown, Maun, Kasane, Palapye, Serowe, Lobatse, Molepolole, Kanye, Mochudi, Tlokweng, Mogoditshane

## Notes

- `auth_state.json` and `.env` are in `.gitignore` — never committed
- Scraping Facebook may violate their Terms of Service — use responsibly
- Re-run `python main.py login` if your session expires
