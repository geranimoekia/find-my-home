#!/usr/bin/env python3
"""
Uses Claude API to parse raw Facebook post text into structured rental listing data.
Handles the messy, informal Botswana rental post style (mix of English & Setswana).
"""
import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None

def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are a data extraction assistant for a Botswana property rental platform.
You receive raw text from Facebook posts advertising houses, flats, or rooms for rent in Botswana.
Your job is to extract structured rental listing data.

Always respond with a single valid JSON object and nothing else.
If a field cannot be determined, use null.
Prices are in BWP (Botswana Pula). Extract only the number (e.g. 4500, not "P4500/month").
"""

EXTRACTION_PROMPT = """Extract rental listing details from this Facebook post.

Post text:
{text}

Return a JSON object with these fields:
{{
  "listing_type": "house" | "flat" | "room" | "plot" | "commercial" | "other",
  "bedrooms": <integer or null>,
  "bathrooms": <integer or null>,
  "price_bwp": <number or null>,
  "price_period": "monthly" | "weekly" | "daily" | null,
  "location": "<area/suburb/city in Botswana or null>",
  "amenities": ["list", "of", "amenities"],
  "contact_phone": "<phone number or null>",
  "contact_name": "<name or null>",
  "available_from": "<date string or 'immediately' or null>",
  "furnished": true | false | null,
  "is_rental": true | false,
  "summary": "<one sentence description of the listing>"
}}"""


def parse_listing(raw_text: str, model: str = "claude-haiku-4-5-20251001") -> dict:
    """
    Parse a single raw post text into a structured listing dict.
    Uses claude-haiku for speed and cost efficiency.
    Returns the parsed dict, or {"is_rental": false} if the post isn't a rental.
    """
    client = _get_client()

    try:
        response = client.messages.create(
            model=model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT.format(text=raw_text[:2000]),
                }
            ],
        )
        content = response.content[0].text.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        return json.loads(content)
    except json.JSONDecodeError:
        return {"is_rental": False, "parse_error": "invalid JSON from model"}
    except Exception as e:
        return {"is_rental": False, "parse_error": str(e)}


def parse_listings_batch(posts: list[dict], model: str = "claude-haiku-4-5-20251001") -> list[dict]:
    """
    Parse a list of raw post dicts (from scrape_groups or scrape_marketplace).
    Merges the AI-extracted fields back into each post dict.
    Filters out posts where is_rental == False.
    """
    results = []
    for i, post in enumerate(posts):
        raw_text = post.get("raw_text") or post.get("title", "")
        if not raw_text:
            continue

        print(f"[parse] Processing post {i + 1}/{len(posts)}...")
        parsed = parse_listing(raw_text, model)

        if not parsed.get("is_rental", True):
            continue

        merged = {**post, **parsed}
        results.append(merged)

    print(f"[parse] {len(results)} rental listings extracted from {len(posts)} posts")
    return results


if __name__ == "__main__":
    # Quick test with a sample Botswana-style rental post
    sample = """
    3 bedroom house for rent in Phakalane.
    P6,500 per month. Borehole water, 2 bathrooms, large yard,
    garage. Available immediately.
    Contact: Thabo 71234567. No pets please.
    """
    result = parse_listing(sample)
    print(json.dumps(result, indent=2))
