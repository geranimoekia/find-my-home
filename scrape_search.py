#!/usr/bin/env python3
"""
Scrapes Facebook Search results for rental listings in Botswana.
Uses Facebook's native search so we don't need to know any group IDs.
Covers posts from groups, pages, profiles, and marketplace all at once.
"""
import os
import re
import time
import json
from urllib.parse import quote_plus
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Search queries to run — covers different ways Batswana post rentals
SEARCH_QUERIES = [
    "house for rent Gaborone",
    "flat for rent Gaborone",
    "room to rent Gaborone",
    "house for rent Francistown",
    "flat for rent Francistown",
    "house for rent Maun",
    "house for rent Botswana",
    "2 bedroom rent Gaborone",
    "3 bedroom rent Gaborone",
    "bachelor flat Gaborone",
]

DEFAULT_SCROLL_ROUNDS = 8


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_post_data(article) -> dict | None:
    """Extract text, image, and link from a single search result article."""
    try:
        text = _clean_text(article.get_text(separator=" "))
        if not text or len(text) < 20:
            return None

        img_tag = article.find("img", src=lambda s: s and "scontent" in s)
        image = img_tag["src"] if img_tag else None

        # Look for a permalink — either a group post, page post, or profile post
        link_tag = article.find(
            "a",
            href=lambda h: h and any(
                p in h for p in ["/groups/", "/posts/", "/permalink/", "/photos/", "story_fbid"]
            ),
        )
        link = None
        if link_tag:
            href = link_tag["href"].split("?")[0]
            link = href if href.startswith("http") else "https://www.facebook.com" + href

        return {
            "source": "fb_search",
            "raw_text": text,
            "image": image,
            "link": link,
        }
    except Exception:
        return None


def scrape_search(
    query: str,
    auth_state_path: str = "auth_state.json",
    scroll_rounds: int = DEFAULT_SCROLL_ROUNDS,
    headless: bool = True,
    debug: bool = False,
) -> list[dict]:
    """
    Run a single Facebook search query and return raw post data.
    """
    if not os.path.exists(auth_state_path):
        print(f"[search] ERROR: {auth_state_path} not found. Run login.py first.")
        return []

    encoded = quote_plus(query)
    # &filters= can be used to filter by "Recent" posts — keeps results fresh
    url = f"https://www.facebook.com/search/posts/?q={encoded}&filters=eyJyZWNlbnRfcG9zdHMiOnsiZmlsdGVyX3ZhbHVlIjoiMSJ9fQ%3D%3D"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=auth_state_path,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        print(f"[search] Searching: \"{query}\"")
        try:
            page.goto(url, timeout=60000)
            time.sleep(5)

            for i in range(scroll_rounds):
                page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
                time.sleep(2 + (i % 3) * 0.5)  # vary delay to look human

            time.sleep(3)
        except Exception as e:
            print(f"[search] Navigation error: {e}")
            browser.close()
            return []

        html = page.content()
        browser.close()

    soup = BeautifulSoup(html, "lxml")

    # Facebook search results render as role="article" divs
    articles = soup.find_all("div", attrs={"role": "article"})

    if debug:
        print(f"[search] Found {len(articles)} articles for \"{query}\"")

    posts = []
    seen = set()

    for article in articles:
        post = _extract_post_data(article)
        if not post:
            continue
        key = post["link"] or post["raw_text"][:120]
        if key in seen:
            continue
        seen.add(key)
        post["query"] = query
        posts.append(post)

    print(f"[search] {len(posts)} posts found for \"{query}\"")
    return posts


def scrape_all_queries(
    queries: list[str] | None = None,
    auth_state_path: str = "auth_state.json",
    scroll_rounds: int = DEFAULT_SCROLL_ROUNDS,
    headless: bool = True,
    debug: bool = False,
) -> list[dict]:
    """
    Run all search queries and deduplicate results by link.
    """
    targets = queries or SEARCH_QUERIES
    all_posts = []
    seen_global = set()

    for q in targets:
        posts = scrape_search(q, auth_state_path, scroll_rounds, headless, debug)
        for p in posts:
            key = p["link"] or p["raw_text"][:120]
            if key not in seen_global:
                seen_global.add(key)
                all_posts.append(p)

    print(f"[search] Total unique posts across all queries: {len(all_posts)}")
    return all_posts


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", help="Search query (default: run all preset queries)")
    parser.add_argument("--auth_state_path", default="auth_state.json")
    parser.add_argument("--scrolls", type=int, default=DEFAULT_SCROLL_ROUNDS)
    parser.add_argument("--no-headless", dest="headless", action="store_false", default=True)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if args.query:
        data = scrape_search(args.query, args.auth_state_path, args.scrolls, args.headless, args.debug)
    else:
        data = scrape_all_queries(None, args.auth_state_path, args.scrolls, args.headless, args.debug)

    print(json.dumps(data, indent=2))
