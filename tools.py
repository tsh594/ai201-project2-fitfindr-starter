"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str

Three required tools + three stretch tools:
- search_listings, suggest_outfit, create_fit_card
- price_comparison, get_trend_insight, (style profile saved/loaded via separate functions)
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()

# ---------- Groq client ----------
def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to .env")
    return Groq(api_key=api_key)

# ---------- Required Tool 1 ----------
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset.
    Returns matching dicts sorted by relevance (keyword overlap).
    """
    listings = load_listings()
    filtered = []

    for item in listings:
        # price filter
        if max_price is not None and item["price"] > max_price:
            continue
        # size filter (case‑insensitive partial match)
        if size is not None and size.lower() not in item["size"].lower():
            continue
        filtered.append(item)

    # Score by keyword overlap with description
    keywords = set(description.lower().split())
    for item in filtered:
        text = (item["title"] + " " + item["description"]).lower()
        score = sum(1 for kw in keywords if kw in text)
        item["_score"] = score

    # Keep only items with score > 0, sort descending by score
    filtered = [i for i in filtered if i["_score"] > 0]
    filtered.sort(key=lambda x: x["_score"], reverse=True)

    # Remove temporary _score field
    for i in filtered:
        del i["_score"]

    return filtered

# ---------- Required Tool 2 ----------
def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Use LLM to suggest 1–2 outfits. Handles empty wardrobe gracefully.
    Also loads saved style profile (stretch memory) and uses it.
    """
    client = _get_groq_client()
    wardrobe_items = wardrobe.get("items", [])

    # --- Load style profile (stretch) ---
    profile = load_style_profile()
    style_note = ""
    if profile and profile.get("preferred_styles"):
        style_note = f"\nThe user's previously preferred styles include: {', '.join(profile['preferred_styles'][:5])}. Use this preference when suggesting outfits.\n"

    if not wardrobe_items:
        # Empty wardrobe – give general styling advice
        prompt = f"""You are a fashion stylist. The user found this thrifted item:
Item: {new_item['title']} ({new_item['category']}) – {new_item['description']}
Colors: {new_item['colors']}  Style tags: {new_item['style_tags']}
{style_note}
The user has NO existing wardrobe items. Give them 2–3 general styling ideas:
- What kind of pieces would pair well with this item?
- Which aesthetics / vibes suit it?
- Any layering or accessory tips?

Keep it helpful, encouraging, and concise (4–6 sentences)."""
    else:
        # Format wardrobe nicely
        wardrobe_text = "\n".join(
            [f"- {i['name']} ({i['category']})" for i in wardrobe_items[:10]]
        )
        prompt = f"""You are a fashion stylist. Suggest 1–2 complete outfits using the NEW thrifted item and pieces from the user's existing wardrobe.

NEW ITEM: {new_item['title']} ({new_item['category']}) – {new_item['description']}
Colors: {new_item['colors']}  Style tags: {new_item['style_tags']}
{style_note}
USER'S WARDROBE:
{wardrobe_text}

Return 1–2 outfit suggestions. For each, name the specific pieces from the wardrobe. Keep it natural and wearable (2–4 sentences total)."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()

# ---------- Required Tool 3 ----------
def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable caption (Instagram/TikTok style).
    """
    if not outfit or not outfit.strip():
        return "[Error] No outfit suggestion provided – cannot create fit card."

    client = _get_groq_client()
    prompt = f"""Write a short, authentic Instagram/TikTok caption for this thrifted outfit.

Item: {new_item['title']} (${new_item['price']}, {new_item['platform']})
Outfit idea: {outfit}

Requirements:
- 2–4 sentences, casual and genuine (like a real OOTD post)
- Mention the item name, price, and platform naturally once each
- Capture the specific vibe (e.g. grunge, cottagecore, streetwear)
- DO NOT sound like a product description. Use emojis sparingly.

Caption:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,   # higher temperature for variety
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# ---------- Stretch Tool 1: Price Comparison ----------
def price_comparison(item: dict, all_listings: Optional[list] = None) -> str:
    """
    Compare the item's price against similar items in the dataset.
    Returns a string assessment (good deal, fair, overpriced).
    """
    if all_listings is None:
        all_listings = load_listings()

    # Find similar items (same category, same condition, overlapping style tags)
    similar = []
    for lst in all_listings:
        if lst["id"] == item["id"]:
            continue
        if lst["category"] != item["category"]:
            continue
        if lst["condition"] != item["condition"]:
            continue
        # at least one common style tag
        if not set(lst["style_tags"]) & set(item["style_tags"]):
            continue
        similar.append(lst)

    if not similar:
        return "⚠️ No comparable items found – price assessment not available."

    prices = [i["price"] for i in similar]
    avg_price = sum(prices) / len(prices)
    item_price = item["price"]

    if item_price < avg_price * 0.8:
        return f"✅ **Great deal!** At ${item_price}, this is about 20% below the average (${avg_price:.2f}) for similar {item['category']} items."
    elif item_price > avg_price * 1.2:
        return f"⚠️ **A bit pricey** – similar items average ${avg_price:.2f}. Consider negotiating or looking for better deals."
    else:
        return f"👍 **Fair price** – similar {item['category']} items sell for around ${avg_price:.2f}. This is right in line."

# ---------- Stretch Tool 2: Trend Awareness ----------
def get_trend_insight(item: dict) -> str:
    """
    Return trend information based on the item's style tags and category.
    Uses LLM to generate up‑to‑date fashion trend commentary.
    """
    client = _get_groq_client()
    prompt = f"""You are a fashion trend forecaster. The user is considering this thrifted item:

Item: {item['title']}
Category: {item['category']}
Style tags: {', '.join(item['style_tags'])}

Write 2 short sentences describing current trends related to this piece.
For example: is this style rising, falling, or having a moment right now?
Keep it realistic and based on general fashion knowledge (no made‑up dates)."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()

# ---------- Stretch Tool 3: Style Profile Memory ----------
PROFILE_FILE = "style_profile.json"

def save_style_profile(profile: dict):
    """Save user style preferences to a JSON file."""
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

def load_style_profile() -> dict:
    """Load previously saved style profile; return empty dict if none."""
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def update_style_profile_from_wardrobe(wardrobe: dict):
    """
    Automatically extract style tags from wardrobe and save as profile.
    Called after a successful outfit suggestion.
    """
    all_tags = []
    for item in wardrobe.get("items", []):
        all_tags.extend(item.get("style_tags", []))
    # keep unique tags, limit to 10 most common
    from collections import Counter
    common = [tag for tag, _ in Counter(all_tags).most_common(10)]
    profile = {
        "preferred_styles": common,
        "last_used_wardrobe_size": len(wardrobe.get("items", []))
    }
    save_style_profile(profile)