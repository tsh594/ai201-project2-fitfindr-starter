📄 FitFindr – AI Shopping Agent

FitFindr helps you find secondhand clothing, style it with your existing wardrobe, and get a shareable fit card.  
This implementation **meets all required features and all stretch features**.

## Tool Inventory

| Tool | Inputs | Output | Purpose |
|------|--------|--------|---------|
| `search_listings` | description (str), size (str or None), max_price (float or None) | list of matching listing dicts | Find items matching user’s query |
| `suggest_outfit` | new_item (dict), wardrobe (dict) | string with outfit ideas | Combine thrifted item with owned pieces |
| `create_fit_card` | outfit (str), new_item (dict) | short caption (2–4 sentences) | Generate social‑media‑ready text |
| **Stretch:** `price_comparison` | item (dict) | string assessment (great deal/fair/pricey) | Compare price to similar listings |
| **Stretch:** `get_trend_insight` | item (dict) | trend description | Add trend‑aware styling context |
| **Stretch:** `save_style_profile` / `load_style_profile` | profile dict / none | – | Remember style preferences across sessions |

## Planning Loop Logic
1. Parse natural language query to extract description, size, max_price.
2. **Call `search_listings`**. If no results → **retry** (remove size, increase budget by 50%). If still none → error out.
3. Select top result → run `price_comparison` and `get_trend_insight`.
4. Call `suggest_outfit` with the item and user’s wardrobe.
5. Call `create_fit_card` (combining outfit + price + trend info).
6. Automatically save style profile from wardrobe.

The agent **does not** call `suggest_outfit` when search fails – it short‑circuits with an error.

## State Management
All intermediate results (parsed query, search results, selected item, outfit suggestion, fit card, price/trend insights) are stored in a `session` dict. The same session flows from `run_agent` to each tool call. No user re‑entry is required – the selected item is automatically passed to `suggest_outfit`.

## Error Handling (with concrete examples)

| Tool | Failure | Agent’s response |
|------|---------|------------------|
| `search_listings` | No results for “designer ballgown size XXS under $5” | Retries without size and budget increased → if still none: “No items found. Please broaden your search.” |
| `suggest_outfit` | Empty wardrobe | Returns general styling advice (e.g., “This knit cardigan goes well with wide‑leg pants, a simple tank, and leather boots.”) |
| `create_fit_card` | Empty outfit string | Returns `[Error] No outfit suggestion provided – cannot create fit card.` |

**Tested failure:** Ran `search_listings` with impossible query → agent returned actionable error and did NOT call further tools.

## Spec Reflection
- **How the spec helped:** The detailed tool interface requirements forced me to design clear boundaries. The explicit error handling table made it obvious what to code for each failure.
- **Divergence & why:** I added the retry logic inside `run_agent` instead of inside `search_listings` – because retrying with different constraints is an agent‑level decision, not a tool responsibility.

## AI Usage Transparency

**Instance 1 (search_listings)**  
- **Directed AI to:** “Implement `search_listings` using the spec: filter by size/price, score by keyword overlap, sort by score, return list.”  
- **What I reviewed & revised:** The AI returned a version that mutated the original listings. I changed it to work on a copy and removed the temporary `_score` field before returning.

**Instance 2 (planning loop + retry)**  
- **Directed AI to:** “Write the `run_agent` planning loop with a retry fallback when search returns empty – remove size first, then increase budget.”  
- **What I reviewed & revised:** The AI’s first version used a hardcoded price increase of $20. I changed it to `max_price * 1.5` to be relative. I also added the `retry_message` so the user knows what changed.

## Example System Output (Transcript)

**Query:** `"vintage graphic tee under $30, size M"`

**Top listing found:**
Y2K Baby Tee — Butterfly Print
💰 $18.00 (depop)
📏 Size: S/M | Condition: excellent
🏷️ y2k, vintage, graphic tee, cottagecore
🔗 Super cute early 2000s baby tee with butterfly graphic. Fitted crop length. Tag says medium but fits like a small...

**Outfit idea:**
Pair this adorable Y2K baby tee with high-waisted denim jeans or a flowy earth-toned skirt. Layer it under a classic denim jacket or a neutral-colored cardigan for a cozy vibe. For a streetwear twist, add sleek sneakers and a simple hat.

**Your fit card:**
Just scored this adorable Y2K Baby Tee for $18 on Depop and I'm obsessed! I've been pairing it with high-waisted denim jeans and a neutral cardigan for a cute, laid-back cottagecore vibe. The butterfly print is so playful and fun 🦋 #thrifted #y2k #cottagecore

**Empty Wardrobe – General Styling Advice:**
Try layering this Y2K baby tee under a classic denim jacket or a neutral‑colored cardigan.
For a streetwear twist, add sleek sneakers and a simple hat.

## Stretch Features Demonstrated
- ✅ **Price Comparison** – Appears in the fit card and console output.  
- ✅ **Style Profile Memory** – `style_profile.json` is saved after each run; second run loads it and influences suggestions.  
- ✅ **Trend Awareness** – `get_trend_insight` adds current trend info to the outfit.  
- ✅ **Retry Logic** – On empty results, agent automatically loosens constraints and explains the change.