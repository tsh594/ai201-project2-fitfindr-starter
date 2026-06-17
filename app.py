"""
app.py – Gradio interface for FitFindr.

Gradio interface for FitFindr. The layout and wiring are already set up —
your job is to fill in handle_query() so it calls run_agent() and maps
the session results to the three output panels.

Run with:
    python app.py

Then open the localhost URL shown in your terminal (usually http://localhost:7860,
but check your terminal — the port may differ).
"""

import gradio as gr
from agent import run_agent
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    if not user_query.strip():
        return "⚠️ Please enter a search query.", "", ""

    wardrobe = get_example_wardrobe() if wardrobe_choice == "Example wardrobe" else get_empty_wardrobe()
    session = run_agent(user_query, wardrobe)

    if session["error"]:
        error_msg = session["error"]
        if session.get("retry_message"):
            error_msg = session["retry_message"] + "\n" + error_msg
        return error_msg, "", ""

    item = session["selected_item"]
    listing_text = f"""**{item['title']}**  
💰 ${item['price']} ({item['platform']})  
📏 Size: {item['size']} | Condition: {item['condition']}  
🏷️ {', '.join(item['style_tags'])}  
🔗 {item['description'][:150]}...
"""

    if session.get("retry_message"):
        listing_text = f"🔄 {session['retry_message']}\n\n{listing_text}"

    return listing_text, session["outfit_suggestion"], session["fit_card"]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)
        with gr.Row():
            query_input = gr.Textbox(label="What are you looking for?", placeholder="e.g. vintage graphic tee under $30, size M", lines=2, scale=3)
            wardrobe_choice = gr.Radio(choices=["Example wardrobe", "Empty wardrobe (new user)"], value="Example wardrobe", label="Wardrobe", scale=1)
        submit_btn = gr.Button("Find it", variant="primary")
        with gr.Row():
            listing_output = gr.Textbox(label="🛍️ Top listing found", lines=8, interactive=False)
            outfit_output = gr.Textbox(label="👗 Outfit idea", lines=8, interactive=False)
            fitcard_output = gr.Textbox(label="✨ Your fit card", lines=8, interactive=False)
        gr.Examples(examples=[["vintage graphic tee under $30", "Example wardrobe"], ["90s track jacket size M", "Example wardrobe"]],
                    inputs=[query_input, wardrobe_choice], label="Try these queries")
        submit_btn.click(handle_query, [query_input, wardrobe_choice], [listing_output, outfit_output, fitcard_output])
        query_input.submit(handle_query, [query_input, wardrobe_choice], [listing_output, outfit_output, fitcard_output])
    return demo

if __name__ == "__main__":
    demo = build_interface()
    demo.launch()