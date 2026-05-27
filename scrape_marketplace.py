#!/usr/bin/env python3
"""
Scrapes Facebook Marketplace for rental listings in Botswana cities.
Adapted from OpenClaw_Facebook_Marketplace_Scraper by Scratchycarl.
"""
import os
import re
import time
import json
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# BWP (Botswana Pula) currency patterns — e.g. "P4,500", "BWP 3000", "4500 pula"
CURRENCY_RE = re.compile(
    r'(?:BWP|P)\s*[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?\s*(?:pula|BWP)',
    re.IGNORECASE
)
FONT_RE = re.compile(r'--x-fontSize\s*:\s*([0-9.]+)px', re.IGNORECASE)

# Botswana cities → Facebook Marketplace city slugs / IDs
# Numeric IDs are more reliable; slugs are fallback guesses
BOTSWANA_CITIES = {
    "Gaborone":    "gaborone",
    "Francistown": "francistown",
    "Maun":        "maun",
    "Kasane":      "kasane",
    "Palapye":     "palapye",
    "Serowe":      "serowe",
    "Lobatse":     "lobatse",
    "Molepolole":  "molepolole",
    "Kanye":       "kanye",
    "Mochudi":     "mochudi",
    "Tlokweng":    "tlokweng",
    "Mogoditshane":"mogoditshane",
}


def _extract_price(element) -> str:
    candidates = []
    for span in element.find_all("span"):
        txt = span.get_text(strip=True)
        m = CURRENCY_RE.search(txt)
        if not m:
            continue
        raw = m.group(0)
        try:
            num = float(re.sub(r"[^\d.]", "", raw.replace(",", "")))
        except Exception:
            num = None
        style = span.get("style") or ""
        fs_m = FONT_RE.search(style)
        font_size = float(fs_m.group(1)) if fs_m else None
        candidates.append({"text": raw, "num": num, "font_size": font_size})

    if candidates:
        with_fs = [c for c in candidates if c["font_size"] is not None]
        if with_fs:
            return max(with_fs, key=lambda c: c["font_size"])["text"]
        numeric = [c for c in candidates if c["num"] is not None]
        if numeric:
            return max(numeric, key=lambda c: c["num"])["text"]
        return candidates[0]["text"]

    for t in element.stripped_strings:
        m = CURRENCY_RE.search(t.strip())
        if m:
            return m.group(0)
    return "N/A"


def _extract_title_location(texts: list, price_text: str = None):
    title = "N/A"
    location = "N/A"
    clean = [t for t in texts if t and t.lower() not in ("sponsored", "ad")]

    if price_text:
        for i, t in enumerate(clean):
            if price_text in t:
                if i + 1 < len(clean):
                    cand = clean[i + 1]
                    if not CURRENCY_RE.search(cand) and len(cand) > 2 and "," not in cand:
                        title = cand
                if i + 2 < len(clean):
                    cand2 = clean[i + 2]
                    if "," in cand2 and len(cand2) < 60:
                        location = cand2
                break

    if title == "N/A":
        for t in clean:
            if not CURRENCY_RE.search(t) and 2 < len(t) < 120 and "," not in t:
                title = t
                break

    if location == "N/A":
        for t in clean:
            if "," in t and len(t) < 60:
                location = t
                break

    return title, location


def _card_from_anchor(a_tag):
    parent = a_tag
    for _ in range(6):
        parent = parent.parent
        if parent is None:
            break
        if parent.find("img") and parent.find("span"):
            return parent
    return a_tag.parent or a_tag


def scrape_marketplace(
    city: str,
    query: str = "house for rent",
    max_price: int = 20000,
    auth_state_path: str = "auth_state.json",
    headless: bool = True,
    debug: bool = False,
) -> list[dict]:
    city_id = BOTSWANA_CITIES.get(city, city.lower().replace(" ", ""))
    if city not in BOTSWANA_CITIES:
        print(f"[marketplace] Warning: '{city}' not in known Botswana cities list. Trying slug '{city_id}'.")

    encoded_query = quote_plus(query)
    url = f"https://www.facebook.com/marketplace/{city_id}/search/?query={encoded_query}&maxPrice={max_price}"

    if not os.path.exists(auth_state_path):
        print(f"[marketplace] ERROR: {auth_state_path} not found. Run login.py first.")
        return []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=auth_state_path,
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"[marketplace] Navigating to {url}")
        try:
            page.goto(url, timeout=60000)
            time.sleep(4)
            # Scroll to trigger lazy-loaded cards
            for _ in range(4):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1.5)
            time.sleep(3)
        except Exception as e:
            print(f"[marketplace] Navigation error: {e}")
            browser.close()
            return []

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")
    results = []
    seen = set()

    anchors = soup.find_all("a", href=lambda h: h and "/marketplace/item/" in h)
    if debug:
        print(f"[marketplace] Found {len(anchors)} item anchors")

    for a in anchors:
        href = a.get("href", "")
        post_url = href if href.startswith("http") else "https://www.facebook.com" + href
        if post_url in seen:
            continue
        seen.add(post_url)

        try:
            card = _card_from_anchor(a)
            img_tag = card.find("img", src=lambda s: s and "scontent" in s)
            image = img_tag["src"] if img_tag else None
            price = _extract_price(card)
            texts = [t.strip() for t in card.stripped_strings if t.strip()]
            title, location = _extract_title_location(texts, price)

            results.append({
                "source": "marketplace",
                "title": title,
                "price": price,
                "location": location,
                "image": image,
                "link": post_url,
            })
        except Exception as e:
            if debug:
                print(f"[marketplace] Parse error: {e}")

    print(f"[marketplace] Scraped {len(results)} listings from {city}")
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="Gaborone")
    parser.add_argument("--query", default="house for rent")
    parser.add_argument("--max_price", type=int, default=20000)
    parser.add_argument("--auth_state_path", default="auth_state.json")
    parser.add_argument("--no-headless", dest="headless", action="store_false", default=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    data = scrape_marketplace(args.city, args.query, args.max_price, args.auth_state_path, args.headless, args.debug)
    print(json.dumps(data, indent=2))
