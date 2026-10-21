"""MiniChatGPT - full-screen chat interface.

Run with:   python app.py
Then open:  http://127.0.0.1:7860

Layout (single page):
  - header:   History button, name, model status, answer-mode dropdown, "New chat"
  - history:  slide-in panel with past chats (saved in the browser)
  - chat:     fills the screen, scrolls, newest message always visible
  - input:    fixed at the bottom (Enter = send, Shift+Enter = new line)

Colors follow the 60-30-10 rule:
  60%  soft white  #F8FAFC  -> page and chat background
  30%  deep navy   #1E293B  -> header, history panel, user messages
  10%  emerald     #10B981  -> send button, active chat, highlights
"""

import argparse
import logging
import uuid

import gradio as gr

from src.chatbot.router import (
    MODE_AUTO,
    SOURCE_ERROR,
    ChatRouter,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

# The chatbot brain from phase 4 (created once when the app starts)
router = ChatRouter()

MAX_SAVED_CHATS = 30  # keep the history list small

# ================================================================ DESIGN
CSS = """
:root {
    --main: #F8FAFC;        /* 60% page + chat background */
    --navy: #1E293B;        /* 30% header, history panel, user bubbles */
    --accent: #10B981;      /* 10% send button, active chat, highlights */
    --accent-dark: #059669;
    --card: #FFFFFF;
    --border: #E2E8F0;
    --text: #0F172A;
    --muted: #64748B;
    --content: 820px;       /* comfortable reading width */
}

/* Full-screen page */
html, body { height: 100%; background: var(--main) !important; }
.gradio-container { max-width: 100% !important; padding: 0 !important; margin: 0 !important;
    background: var(--main) !important; }
.gradio-container > .main, .gradio-container .wrap.main { padding: 0 !important; }
footer { display: none !important; }

/* ---------- Header (navy) ---------- */
#header { position: sticky; top: 0; z-index: 20; background: var(--navy) !important;
    padding: 8px 16px !important; gap: 10px !important; align-items: center !important;
    flex-wrap: nowrap !important; min-height: 56px; border: none !important; }
#header .block, #header .form { background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important; }
#brand { font-size: 17px; font-weight: 650; color: #fff; white-space: nowrap;
    display: flex; align-items: center; gap: 10px; }
#brand .logo { width: 28px; height: 28px; border-radius: 8px; background: var(--accent);
    color: #fff; font-size: 14px; font-weight: 700; display: flex; align-items: center;
    justify-content: center; }
#brand, #brand .name { color: #FFFFFF !important; }
#brand .logo { flex-shrink: 0; }
#brand .status, #brand .status span { font-size: 12px; font-weight: 400; color: #CBD5E1 !important; }
#brand .status { display: flex; gap: 10px; }
#brand .dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%;
    margin-right: 4px; vertical-align: 1px; }
#brand .on { background: var(--accent); }
#brand .off { background: #F59E0B; }
#header #history-btn { font-size: 18px !important; width: 42px !important; padding: 0 !important; }
#history #new-chat { width: 100% !important; justify-content: flex-start !important; padding: 0 14px !important;
    font-size: 14px !important; margin-bottom: 8px; }
#history-btn, #new-chat { flex: 0 0 auto !important; min-width: 0 !important;
    background: transparent !important; border: 1px solid #475569 !important; color: #fff !important;
    border-radius: 10px !important; font-weight: 500 !important; padding: 0 14px !important;
    height: 38px; box-shadow: none !important; }
#history-btn:hover, #new-chat:hover { border-color: var(--accent) !important;
    background: rgba(16,185,129,.12) !important; }
#mode-select { min-width: 230px !important; max-width: 250px; }
#mode-select .wrap { border: 1px solid #475569 !important; border-radius: 10px !important;
    background: #0F172A !important; min-height: 38px; }
#mode-select input { color: #fff !important; font-size: 14px !important; padding-right: 6px !important;
    text-overflow: ellipsis; }
#mode-select svg { color: #fff !important; fill: #fff !important; }
.spacer { flex-grow: 1 !important; }

/* ---------- History panel (slides over the chat) ---------- */
/* ---------- Body: history panel + chat side by side ---------- */
#body { flex-wrap: nowrap !important; gap: 0 !important; align-items: stretch !important;
    margin-top: calc(-1 * var(--layout-gap, 16px)) !important; }
#main { min-width: 0 !important; gap: 0 !important; }
#history { flex: 0 0 280px !important; width: 280px !important; max-width: 280px;
    height: calc(100dvh - 64px); position: sticky; top: 64px; overflow-y: auto;
    background: var(--navy) !important; padding: 16px 12px !important;
    border: none !important; border-radius: 0 !important; gap: 10px !important; }
#history .block, #history .form, #history fieldset { background: transparent !important;
    border: none !important; box-shadow: none !important; padding: 0 !important; }
#history-title { color: #94A3B8; font-size: 12px; text-transform: uppercase; letter-spacing: .06em;
    padding: 0 6px; }
#history-list .wrap { flex-direction: column !important; gap: 4px !important; }
#history-list label { width: 100% !important; background: transparent !important;
    border: 1px solid transparent !important; border-radius: 10px !important; padding: 9px 10px !important;
    cursor: pointer; }
#history-list label:hover { background: rgba(255,255,255,.06) !important; }
#history-list label.selected, #history-list label:has(input:checked) {
    background: rgba(16,185,129,.18) !important; border-color: var(--accent) !important; }
#history-list label span { color: #E2E8F0 !important; font-size: 14px !important;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#history-list input[type=radio] { display: none !important; }
#history-empty { color: #94A3B8; font-size: 13px; padding: 4px 6px; }
#clear-history { background: transparent !important; border: 1px solid #475569 !important;
    color: #CBD5E1 !important; border-radius: 10px !important; font-weight: 400 !important;
    box-shadow: none !important; }
#clear-history:hover { border-color: #F87171 !important; color: #FCA5A5 !important; }

/* ---------- Chat area (fills the screen, scrolls) ---------- */
#chat { border: none !important; background: var(--main) !important; box-shadow: none !important;
    border-radius: 0 !important; height: calc(100dvh - 215px) !important; }
#chat .bubble-wrap, #chat > div { background: var(--main) !important; }
#chat .message-wrap { max-width: var(--content); margin: 0 auto !important;
    padding: 24px 16px 8px !important; }
#chat .message-row { margin: 6px 0 !important; }
/* User: right side, navy bubble */
#chat .user-row { max-width: 75% !important; }
#chat .message.user { background: var(--navy) !important; border: none !important;
    border-radius: 18px 18px 4px 18px !important; padding: 10px 16px !important; max-width: none !important; }
#chat .message.user, #chat .message.user * { color: #fff !important; }
/* AI: left side, white card */
#chat .message.bot { background: var(--card) !important; border: 1px solid var(--border) !important;
    border-radius: 18px 18px 18px 4px !important; padding: 12px 18px !important;
    box-shadow: 0 1px 2px rgba(15,23,42,.04) !important; max-width: 100% !important; }
#chat .message, #chat .message * { font-size: 15.5px; line-height: 1.65; }
#chat .message.bot * { color: var(--text); }
#chat .message.bot a { color: var(--accent-dark) !important; }
#chat .message.bot code { background: #F1F5F9; }
#chat sub, #chat sub * { color: var(--muted) !important; font-size: 12px !important; }
/* Small grey copy icons; hide the duplicate clear icon ("New chat" does this) */
#chat .message-buttons button, #chat .message-buttons button * { color: var(--muted) !important;
    border-color: transparent !important; background: transparent !important; }
#chat button[aria-label="Clear"] { display: none !important; }
/* Welcome message in the centre */
#chat .placeholder-content, #chat .placeholder { display: flex; align-items: center;
    justify-content: center; height: 100%; text-align: center; }
#chat .placeholder h2 { font-size: 26px; font-weight: 600; margin-bottom: 6px; color: var(--navy); }
#chat .placeholder p { color: var(--muted); }

/* ---------- Input bar (fixed at the bottom) ---------- */
#input-area { position: sticky; bottom: 0; background: var(--main) !important;
    padding: 4px 16px 4px !important; gap: 4px !important; }
#input-area .form { background: transparent !important; border: none !important; }
#input-area > .block, #input-area .html-container { padding: 0 !important; }
#input-box { max-width: var(--content); margin: 0 auto !important; width: 100%; }
#input-box, #input-box .block { background: transparent !important; border: none !important;
    box-shadow: none !important; padding: 0 !important; }
#input-box label { background: transparent !important; border: none !important;
    padding: 0 !important; box-shadow: none !important; }
#input-box .input-container { background: var(--card) !important;
    border: 1px solid var(--border) !important; border-radius: 24px !important;
    padding: 6px 8px 6px 18px !important; align-items: flex-end;
    box-shadow: 0 2px 8px rgba(15,23,42,.06) !important; }
#input-box .input-container:focus-within { border-color: var(--accent) !important; }
#input-box textarea { background: transparent !important; border: none !important;
    box-shadow: none !important; font-size: 15.5px !important; padding: 8px 0 !important;
    color: var(--text) !important; }
#input-box button { background: var(--accent) !important; color: #fff !important;
    border-radius: 50% !important; width: 36px !important; height: 36px !important;
    min-width: 36px !important; border: none !important; }
#input-box button:hover { background: var(--accent-dark) !important; }
#input-box button svg, #input-box button * { color: #fff !important; fill: #fff; }
#footer-note { text-align: center; color: var(--muted); font-size: 12px; padding: 6px 0 4px; }

/* ---------- Mobile ---------- */
@media (max-width: 640px) {
    #header { padding: 8px 8px !important; gap: 6px !important; }
    #brand .status, #brand .name { display: none; }
    #mode-select { min-width: 130px !important; }
    #history-btn { padding: 0 !important; }
    /* Phone: the open panel takes the whole width; picking a chat closes it */
    #history { flex: 1 1 100% !important; width: 100% !important; max-width: 100%; }
    #body:has(#history) #main { display: none !important; }
    #footer-note { display: none; }
    #chat .user-row { max-width: 88% !important; }
}
"""

WELCOME = """
## What can I help with?
Ask me anything.
"""

# Shown instead of technical error details (those are printed in the terminal only)
ERROR_MESSAGE = "Sorry, I couldn't answer that right now. Please try again in a moment."


# ================================================================ CHAT LOGIC
def brand_html():
    """Header title (no technical details on the screen)."""
    return '<div id="brand"><span class="logo">M</span><span class="name">MiniChatGPT</span></div>'


def format_reply(text, source, note):
    """Show only the answer. Which model answered is logged in the terminal, not on screen."""
    if source == SOURCE_ERROR:
        return ERROR_MESSAGE
    return text


def respond(message, display, memory, mode):
    """Called when the user sends a message.

    display: messages shown on screen (with labels)
    memory:  clean messages sent to Gemini as chat memory
    """
    message = (message or "").strip()
    if not message:
        yield "", display, memory
        return

    # Show the user's message right away, and "Thinking..." for the bot
    display = display + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "_Thinking…_"},
    ]
    yield "", display, memory

    # Update the bot's message every time a new piece of the answer arrives
    reply, source, note = "", SOURCE_ERROR, None
    for reply, source, note in router.stream(message, memory, mode):
        display[-1] = {"role": "assistant", "content": format_reply(reply, source, note)}
        yield "", display, memory

    # Backend only: print who answered in the terminal (never shown on screen)
    logging.info("Answered by: %s%s", source, f" ({note})" if note else "")

    # Only remember real answers (not error messages)
    if source != SOURCE_ERROR:
        memory = memory + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
    yield "", display, memory


# ================================================================ CHAT HISTORY
def chat_title(display):
    """Use the first user message as the chat's title."""
    for item in display:
        if item["role"] == "user":
            text = " ".join(str(item["content"]).split())
            return text[:40] + ("…" if len(text) > 40 else "")
    return "New chat"


def save_chat(chats, chat_id, display, memory):
    """Add or update one chat in the saved list (newest first)."""
    chats = [c for c in (chats or []) if c["id"] != chat_id]
    chats.insert(0, {"id": chat_id, "title": chat_title(display),
                     "display": display, "memory": memory})
    return chats[:MAX_SAVED_CHATS]


def history_list(chats, selected=None):
    """Update the list of past chats in the history panel."""
    choices = [(c["title"], c["id"]) for c in (chats or [])]
    return gr.Radio(choices=choices, value=selected)


def history_empty_note(chats):
    return gr.HTML(visible=not chats)


# ================================================================ LAYOUT
with gr.Blocks(title="MiniChatGPT", fill_height=True, fill_width=True) as demo:
    memory = gr.State([])        # clean chat sent to Gemini
    display = gr.State([])       # chat shown on screen
    chat_id = gr.State(None)     # id of the open chat
    panel_open = gr.State(False)
    # Saved chats live in the browser (localStorage), so they survive a refresh
    chats = gr.BrowserState([], storage_key="minichatgpt-chats")

    # Always "Auto": Gemini first, my trained model as fallback (decided in the backend)
    mode = gr.State(MODE_AUTO)

    # Header: only the menu (hamburger) button and the name
    with gr.Row(elem_id="header", equal_height=True):
        history_btn = gr.Button("☰", elem_id="history-btn", scale=0, size="sm")
        gr.HTML(brand_html())
        gr.HTML("", elem_classes="spacer")

    # Body: history panel on the left (when open) + chat on the right.
    # They sit side by side, so the chat shrinks to make room for the panel.
    with gr.Row(elem_id="body", equal_height=False):
        # Sidebar with all buttons (hidden until the ☰ button is clicked)
        with gr.Column(visible=False, elem_id="history", scale=0, min_width=0) as history_panel:
            clear_btn = gr.Button("＋ New chat", elem_id="new-chat", size="sm")
            gr.HTML('<div id="history-title">Your chats</div>')
            empty_note = gr.HTML('<div id="history-empty">No saved chats yet.</div>')
            history = gr.Radio(choices=[], show_label=False, container=False, elem_id="history-list")
            clear_history_btn = gr.Button("Clear history", elem_id="clear-history", size="sm")

        with gr.Column(elem_id="main", scale=1):
            # Chat area: fills the remaining space and scrolls to the newest message
            chatbot = gr.Chatbot(
                elem_id="chat",
                show_label=False,
                placeholder=WELCOME,
                autoscroll=True,
                avatar_images=(None, None),
                buttons=["copy"],
                scale=1,
            )

            # Input bar: fixed at the bottom
            with gr.Column(elem_id="input-area"):
                textbox = gr.Textbox(
                    placeholder="Message MiniChatGPT…",
                    show_label=False,
                    lines=1,
                    max_lines=8,
                    autofocus=True,
                    submit_btn="➤",
                    elem_id="input-box",
                )
                gr.HTML('<div id="footer-note">Enter to send · Shift + Enter for a new line · '
                        'MiniChatGPT can make mistakes. Check important information.</div>')

    # ------------------------------------------------------------ events
    def run_chat(message, display_value, memory_value, mode_value, chats_value, chat_id_value):
        """Send a message, stream the answer, then save the chat to history."""
        shown, mem, text = display_value, memory_value, ""
        for text, shown, mem in respond(message, display_value, memory_value, mode_value):
            yield text, shown, mem, shown, gr.skip(), gr.skip(), gr.skip(), gr.skip()
        if not shown:
            return
        chat_id_value = chat_id_value or uuid.uuid4().hex[:10]
        chats_value = save_chat(chats_value, chat_id_value, shown, mem)
        yield (text, shown, mem, shown, chats_value, chat_id_value,
               history_list(chats_value, chat_id_value), history_empty_note(chats_value))

    chat_inputs = [textbox, display, memory, mode, chats, chat_id]
    chat_outputs = [textbox, chatbot, memory, display, chats, chat_id, history, empty_note]

    # Enter (and the send button inside the box) both trigger "submit"
    textbox.submit(run_chat, chat_inputs, chat_outputs)

    # New chat: empty screen and memory (old chat stays in history), then close the sidebar
    def new_chat():
        return [], [], [], "", None, gr.Radio(value=None), False, gr.Column(visible=False)

    clear_btn.click(new_chat, None,
                    [chatbot, display, memory, textbox, chat_id, history, panel_open, history_panel])
    # Gradio's own clear icon (hidden) must also reset the memory
    chatbot.clear(lambda: ([], [], "", None), None, [display, memory, textbox, chat_id])

    # Open / close the history panel
    def toggle_panel(is_open):
        return not is_open, gr.Column(visible=not is_open)

    history_btn.click(toggle_panel, panel_open, [panel_open, history_panel])

    # Open a saved chat
    def open_chat(selected_id, chats_value):
        for chat in chats_value or []:
            if chat["id"] == selected_id:
                return (chat["display"], chat["display"], chat["memory"], selected_id,
                        False, gr.Column(visible=False))
        return gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

    history.input(open_chat, [history, chats],
                  [chatbot, display, memory, chat_id, panel_open, history_panel])

    # Delete all saved chats
    def clear_history():
        return [], history_list([]), history_empty_note([]), [], [], [], None

    clear_history_btn.click(clear_history, None,
                            [chats, history, empty_note, chatbot, display, memory, chat_id])

    # Fill the history list when the page opens
    demo.load(lambda c: (history_list(c), history_empty_note(c)), chats, [history, empty_note])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the MiniChatGPT app")
    parser.add_argument("--share", action="store_true", help="create a public link")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()

    theme = gr.themes.Soft(primary_hue="emerald", neutral_hue="slate",
                           font=[gr.themes.GoogleFont("Inter"), "sans-serif"])
    demo.queue().launch(server_port=args.port, share=args.share, css=CSS, theme=theme)