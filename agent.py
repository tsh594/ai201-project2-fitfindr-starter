"""
agent.py – Planning loop with state management, error handling, and retry fallback.

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import (
    search_listings, suggest_outfit, create_fit_card,
    price_comparison, get_trend_insight, update_style_profile_from_wardrobe
)

def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "price_assessment": None,
        "trend_insight": None,
        "error": None,
        "retry_message": None,
    }

def _parse_query(query: str) -> dict:
    query_lower = query.lower()
    words = query_lower.split()
    description = []
    size = None
    max_price = None

    size_keywords = ["size", "s", "m", "l", "xl", "xxl", "xs", "xxs", "medium", "large", "small"]
    for i, w in enumerate(words):
        if w in size_keywords or (w.startswith("size") and i+1 < len(words)):
            if w.startswith("size") and i+1 < len(words):
                size = words[i+1].upper()
            elif w in ["s","m","l","xl","xs","xxl","xxs"]:
                size = w.upper()
            elif w in ["small","medium","large"]:
                size = w[0].upper()
        elif "$" in w or (w.isdigit() and i+1 < len(words) and words[i+1] == "under"):
            price_str = w.replace("$", "").replace(",", "")
            if price_str.isdigit():
                max_price = float(price_str)

    for w in words:
        if not (w in ["under", "size"] or (size and w == size.lower()) or
                (max_price and w.replace("$","").isdigit())):
            description.append(w)
    if not description:
        description = ["clothing"]

    return {
        "description": " ".join(description),
        "size": size,
        "max_price": max_price,
    }

def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)
    session["parsed"] = _parse_query(query)

    results = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )
    session["search_results"] = results

    retry_attempted = False
    if not results:
        orig_size = session["parsed"]["size"]
        orig_price = session["parsed"]["max_price"]
        new_size = None
        new_price = orig_price * 1.5 if orig_price else None

        results = search_listings(
            description=session["parsed"]["description"],
            size=new_size,
            max_price=new_price,
        )
        if results:
            session["retry_message"] = f"No exact matches found. Removed size filter{' and increased budget' if orig_price else ''} – showing {len(results)} alternative items."
            session["parsed"]["size"] = new_size
            session["parsed"]["max_price"] = new_price
            session["search_results"] = results
            retry_attempted = True

    if not session["search_results"]:
        session["error"] = f"❌ No items found for '{session['parsed']['description']}'." + \
                           (" Try a different size, higher budget, or more general keywords." if not retry_attempted else " Even after loosening constraints, nothing matches. Please broaden your search.")
        return session

    session["selected_item"] = session["search_results"][0]
    session["price_assessment"] = price_comparison(session["selected_item"])
    session["trend_insight"] = get_trend_insight(session["selected_item"])
    session["outfit_suggestion"] = suggest_outfit(session["selected_item"], session["wardrobe"])

    enriched_outfit = session["outfit_suggestion"] + "\n\n" + session["price_assessment"] + "\n\n" + session["trend_insight"]
    session["fit_card"] = create_fit_card(enriched_outfit, session["selected_item"])

    update_style_profile_from_wardrobe(session["wardrobe"])

    return session