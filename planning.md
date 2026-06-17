# FitFindr — planning.md

## Tools

### Tool 1: search_listings
**What it does:** Filters mock listings by keywords, size, and max price, then sorts by relevance.  
**Inputs:** description (str), size (str | None), max_price (float | None)  
**Returns:** list of dicts – each dict contains id, title, description, category, style_tags, size, condition, price, colors, brand, platform.  
**Failure mode:** If no matches, returns empty list []. The agent then retries with loosened constraints or stops with a helpful error.

### Tool 2: suggest_outfit
**What it does:** Uses Groq LLM to suggest 1–2 outfits combining a new thrifted item with existing wardrobe pieces.  
**Inputs:** new_item (dict), wardrobe (dict with "items" list)  
**Returns:** string – outfit suggestions.  
**Failure mode:** If wardrobe is empty, LLM gives general styling advice instead of crashing.

### Tool 3: create_fit_card
**What it does:** Generates a short, social‑media‑ready caption.  
**Inputs:** outfit (str), new_item (dict)  
**Returns:** string – 2–4 sentence caption.  
**Failure mode:** If outfit is empty, returns error message string.

### Additional Tools (Stretch)
- **price_comparison(item, all_listings)** – compares price to similar items. Returns assessment (great deal / fair / pricey).  
- **get_trend_insight(item)** – uses LLM to describe current trends related to the item.  
- **save_style_profile / load_style_profile** – persists user style preferences across sessions.

## Planning Loop
After parsing the query, the loop:
1. Calls `search_listings(parsed description, size, max_price)`.
2. If results are empty → **retry** by removing size filter and increasing budget by 50%. If still empty → set error and stop.
3. Pick top result → store in session.
4. Call `price_comparison` and `get_trend_insight` (stretch) – store in session.
5. Call `suggest_outfit(selected_item, wardrobe)`.
6. Call `create_fit_card(outfit + price + trend, selected_item)`.
7. Update style profile from wardrobe (stretch memory).

The loop adapts: it does NOT call suggest_outfit if search fails, and it automatically retries on empty results.

## State Management
A `session` dict holds everything:
- `parsed` (extracted query parts)
- `search_results`, `selected_item`
- `outfit_suggestion`, `fit_card`
- `price_assessment`, `trend_insight`
- `error`, `retry_message`

Each tool’s output is stored, and subsequent tools read directly from the session – no user re‑entry.

## Error Handling Table

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match | Retry with loosened constraints; if still none → stop with specific error message (“No items found. Try a different size or higher budget.”) |
| suggest_outfit | Wardrobe empty | Returns general styling advice (“Pair this with baggy jeans and sneakers…”) |
| create_fit_card | Outfit input missing/incomplete | Returns error string: “[Error] No outfit suggestion provided…” |

## Architecture Diagram
```text
User query
    │
    ▼
[Parse query] → session["parsed"]
    │
    ▼
search_listings(desc, size, price)
    │
    ├── empty → retry (remove size / increase budget)
    │           ├── still empty → error & return
    │           └── has results → continue
    │
    ▼
Store top result + price_comparison + trend_insight (stretch)
    │
    ▼
suggest_outfit(selected_item, wardrobe)
    │
    ▼
create_fit_card(outfit + price + trend, selected_item)
    │
    ▼
Update style profile → Return session
```
## Complete Interaction Walkthrough

**Example user query:** `"vintage graphic tee under $30, size M"`

**Step 1 – Parse**  
`_parse_query()` extracts:
- `description = "vintage graphic tee"`
- `size = "M"`
- `max_price = 30.0`

**Step 2 – Search**  
`search_listings(description, size, max_price)` is called.  
It returns 3 matching listings (e.g., `lst_006` Graphic Tee, `lst_002` Y2K Baby Tee, `lst_033` Vintage Band Tee).  
They are sorted by relevance; the top is `lst_006` (score 3).  
`selected_item = lst_006`

**Step 3 – Price & Trend (stretch)**  
`price_comparison()` compares `lst_006` to similar tops → returns *"Fair price – similar tops sell for around $22."*  
`get_trend_insight()` returns *"Graphic tees are having a 90s revival right now."*

**Step 4 – Suggest outfit**  
`suggest_outfit(selected_item, wardrobe)` uses the LLM and the user's example wardrobe to return:  
*"Pair this faded band tee with your baggy straight‑leg jeans and chunky white sneakers. Add the black denim jacket for a layered 90s grunge look."*

**Step 5 – Fit card**  
`create_fit_card(outfit_suggestion, selected_item)` generates:  
*"Thrifted this faded band tee for $24 on Depop – it's giving 90s grunge with my baggy jeans 🖤 #thrifted #ootd"*

**Error path** – if `search_listings` had returned empty, the agent would have **retried** by removing size and increasing budget, and if still empty, it would have stopped with a clear error message without calling the other tools.

## AI Tool Plan

**Instance 1 – `search_listings`**  
- **Tool used:** Claude  
- **Input given:** Tool 1 spec from `planning.md` (inputs, return value, failure mode) + note to use `load_listings()`.  
- **Expected output:** A function that filters by size/price, scores by keyword overlap, sorts, and returns a list.  
- **Verification:** Reviewed the code to ensure it works on a copy (doesn't mutate original data) and removes the temporary `_score` field. Tested with 3 queries: `"vintage tee"`, `"jacket size M under $50"`, `"designer ballgown XXS under $5"` – the last returned `[]`.

**Instance 2 – Planning loop + retry logic**  
- **Tool used:** ChatGPT  
- **Input given:** Architecture diagram + Planning Loop and State Management sections from `planning.md`.  
- **Expected output:** `run_agent()` with conditional branches and state storage.  
- **Verification:** Checked that it branches on empty results, that it stores `selected_item` and `outfit_suggestion` in the session, and that it does **not** call `suggest_outfit` when search fails. I revised the retry budget from a hardcoded `+20` to `* 1.5` so it's relative.