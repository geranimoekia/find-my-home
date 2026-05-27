#!/usr/bin/env python3
"""
Oversear Rental Scraper — CLI entry point.

Usage examples:

  # Step 1: log in once and save session
  python main.py login

  # Step 2: search Facebook for rental posts (recommended)
  python main.py search

  # Search a custom query
  python main.py search --query "house for rent Gaborone"

  # Step 3: scrape Facebook Marketplace
  python main.py marketplace --city Gaborone

  # Scrape everything and save to JSON
  python main.py all --output listings.json
"""
import argparse
import json
import os
from dotenv import load_dotenv

load_dotenv()


def cmd_login(_args):
    from login import login_and_save
    login_and_save()


def cmd_search(args):
    from scrape_search import scrape_search, scrape_all_queries
    from parse_with_ai import parse_listings_batch

    if args.query:
        raw = scrape_search(
            query=args.query,
            auth_state_path=args.auth,
            scroll_rounds=args.scrolls,
            headless=not args.show,
            debug=args.debug,
        )
    else:
        raw = scrape_all_queries(
            auth_state_path=args.auth,
            scroll_rounds=args.scrolls,
            headless=not args.show,
            debug=args.debug,
        )

    listings = parse_listings_batch(raw)
    _output(listings, args.output)


def cmd_marketplace(args):
    from scrape_marketplace import scrape_marketplace
    from parse_with_ai import parse_listings_batch

    raw = scrape_marketplace(
        city=args.city,
        query=args.query,
        max_price=args.max_price,
        auth_state_path=args.auth,
        headless=not args.show,
        debug=args.debug,
    )
    listings = parse_listings_batch(raw)
    _output(listings, args.output)


def cmd_all(args):
    from scrape_search import scrape_all_queries
    from scrape_marketplace import scrape_marketplace, BOTSWANA_CITIES
    from parse_with_ai import parse_listings_batch

    print("[main] Running Facebook Search for all preset queries...")
    search_posts = scrape_all_queries(
        auth_state_path=args.auth,
        headless=not args.show,
        debug=args.debug,
    )

    print("[main] Scraping Marketplace for all Botswana cities...")
    mp_posts = []
    for city in BOTSWANA_CITIES:
        mp_posts.extend(
            scrape_marketplace(
                city=city,
                query="house for rent",
                auth_state_path=args.auth,
                headless=not args.show,
                debug=args.debug,
            )
        )

    all_raw = search_posts + mp_posts
    print(f"[main] Total raw posts: {len(all_raw)}. Parsing with AI...")
    listings = parse_listings_batch(all_raw)
    _output(listings, args.output)


def _output(listings: list, path: str | None):
    out = json.dumps(listings, indent=2, ensure_ascii=False)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[main] Saved {len(listings)} listings to {path}")
    else:
        print(out)


def main():
    parser = argparse.ArgumentParser(
        description="Oversear — Botswana rental listing scraper"
    )
    parser.add_argument("--auth", default="auth_state.json", help="Path to Facebook auth state file")
    parser.add_argument("--output", "-o", help="Save results to this JSON file")
    parser.add_argument("--show", action="store_true", help="Show the browser window (disable headless)")
    parser.add_argument("--debug", action="store_true")

    sub = parser.add_subparsers(dest="command", required=True)

    # login
    sub.add_parser("login", help="Log into Facebook and save session")

    # search
    p_search = sub.add_parser("search", help="Search Facebook posts for rentals")
    p_search.add_argument("--query", help="Custom search query (default: runs all preset Botswana queries)")
    p_search.add_argument("--scrolls", type=int, default=8, help="Scroll rounds per query")

    # marketplace
    p_mp = sub.add_parser("marketplace", help="Scrape Facebook Marketplace")
    p_mp.add_argument("--city", default="Gaborone")
    p_mp.add_argument("--query", default="house for rent")
    p_mp.add_argument("--max_price", type=int, default=20000)

    # all
    sub.add_parser("all", help="Run all search queries + Marketplace for all cities")

    args = parser.parse_args()

    dispatch = {
        "login":       cmd_login,
        "search":      cmd_search,
        "marketplace": cmd_marketplace,
        "all":         cmd_all,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
