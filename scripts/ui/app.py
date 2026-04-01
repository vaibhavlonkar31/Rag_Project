# scripts/ui/app.py

import streamlit as st
import requests
from pathlib import Path
import sys
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from ui.components.chat_box import render_chat_box
from ui.components.citations_viewer import render_citations
from ui.components.file_uploader import render_file_uploader

st.set_page_config(
    page_title="DocMind AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "input_key" not in st.session_state:
    st.session_state.input_key = 0
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "chat"

BACKEND_URL = "http://127.0.0.1:8000"

# ── Global CSS & Animations ───────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;1,300&display=swap');

:root {
    --bg:        #070710;
    --bg2:       #0e0e1a;
    --bg3:       #14142a;
    --border:    rgba(120,100,255,0.15);
    --border2:   rgba(120,100,255,0.25);
    --accent:    #7864ff;
    --accent2:   #ff6b9d;
    --accent3:   #00d4aa;
    --text:      #f0eeff;
    --text2:     rgba(240,238,255,0.55);
    --text3:     rgba(240,238,255,0.28);
    --glow:      rgba(120,100,255,0.12);
    --glow2:     rgba(255,107,157,0.08);
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Outfit', sans-serif !important;
}

/* Animated mesh background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse 70% 60% at 15% 5%,  rgba(120,100,255,0.09) 0%, transparent 65%),
        radial-gradient(ellipse 50% 40% at 85% 90%, rgba(255,107,157,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 40% 50% at 50% 50%, rgba(0,212,170,0.04) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
    animation: meshShift 12s ease-in-out infinite alternate;
}

@keyframes meshShift {
    0%   { opacity: 1; transform: scale(1); }
    100% { opacity: 0.7; transform: scale(1.05); }
}

[data-testid="stHeader"], footer, #MainMenu { display: none !important; }

section.main > div {
    padding: 0 !important;
    max-width: 1000px !important;
    margin: 0 auto !important;
    position: relative;
    z-index: 1;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }

/* ── Input ── */
[data-testid="stTextInput"] input {
    background: rgba(120,100,255,0.06) !important;
    border: 1px solid var(--border2) !important;
    border-radius: 14px !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.92rem !important;
    padding: 0.8rem 1.1rem !important;
    transition: all 0.3s ease !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(120,100,255,0.12), 0 0 20px rgba(120,100,255,0.08) !important;
    outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--text3) !important; }

/* ── Buttons ── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, var(--accent) 0%, #9b6dff 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    letter-spacing: 0.02em !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 15px rgba(120,100,255,0.25) !important;
}
[data-testid="stButton"] > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(120,100,255,0.4) !important;
}
[data-testid="stButton"] > button:active {
    transform: translateY(0px) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: rgba(120,100,255,0.04) !important;
    border: 1px dashed var(--border2) !important;
    border-radius: 16px !important;
    padding: 0.8rem !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] > div { border-top-color: var(--accent) !important; }

/* ── Code blocks ── */
[data-testid="stCode"] {
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── Page load animation ── */
@keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}
.anim-1 { animation: fadeSlideUp 0.5s ease both; }
.anim-2 { animation: fadeSlideUp 0.5s 0.1s ease both; }
.anim-3 { animation: fadeSlideUp 0.5s 0.2s ease both; }
.anim-4 { animation: fadeSlideUp 0.5s 0.3s ease both; }

/* ── Pulse dot ── */
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.75); }
}
.pulse-dot {
    width: 7px; height: 7px;
    background: var(--accent3);
    border-radius: 50%;
    display: inline-block;
    animation: pulse 2s ease-in-out infinite;
}

/* ── Shimmer on brand name ── */
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
}
.brand-shimmer {
    background: linear-gradient(90deg,
        #f0eeff 0%, #7864ff 40%, #ff6b9d 60%, #f0eeff 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: shimmer 4s linear infinite;
}

/* ── Tab nav ── */
.tab-nav {
    display: flex;
    gap: 0.4rem;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.3rem;
    width: fit-content;
}
.tab-btn {
    padding: 0.45rem 1.2rem;
    border-radius: 10px;
    font-family: 'Outfit', sans-serif;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: all 0.2s ease;
    letter-spacing: 0.02em;
}
.tab-btn.active {
    background: linear-gradient(135deg, var(--accent), #9b6dff);
    color: #fff;
    box-shadow: 0 3px 12px rgba(120,100,255,0.3);
}
.tab-btn.inactive {
    background: transparent;
    color: var(--text2);
}
.tab-btn.inactive:hover { background: rgba(120,100,255,0.08); color: var(--text); }

/* ── History card ── */
@keyframes cardIn {
    from { opacity: 0; transform: translateX(-12px); }
    to   { opacity: 1; transform: translateX(0); }
}
.history-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s, box-shadow 0.2s;
    animation: cardIn 0.35s ease both;
}
.history-card:hover {
    border-color: var(--border2);
    box-shadow: 0 4px 20px var(--glow);
}

/* ── Typing cursor ── */
@keyframes blink { 0%,100% { opacity:1; } 50% { opacity:0; } }
.cursor { animation: blink 1s step-end infinite; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="anim-1" style="padding: 2.2rem 2.5rem 0.5rem;">
    <div style="display:flex; align-items:center; gap:0.9rem; margin-bottom:0.4rem;">
        <div style="
            width:42px; height:42px;
            background: linear-gradient(135deg,#7864ff,#ff6b9d);
            border-radius:12px;
            display:flex; align-items:center; justify-content:center;
            font-size:1.3rem;
            box-shadow: 0 4px 20px rgba(120,100,255,0.4);
        ">◈</div>
        <span class="brand-shimmer" style="
            font-family:'Outfit',sans-serif;
            font-size:2.1rem; font-weight:800;
            letter-spacing:-0.03em;
        ">DocMind AI</span>
        <span style="
            font-family:'JetBrains Mono',monospace;
            font-size:0.65rem; color:#00d4aa;
            background:rgba(0,212,170,0.1);
            border:1px solid rgba(0,212,170,0.25);
            border-radius:99px; padding:0.2rem 0.65rem;
        ">v2.0 · RAG</span>
        <span class="pulse-dot" style="margin-left:0.2rem;"></span>
    </div>
    <p style="
        font-family:'JetBrains Mono',monospace;
        font-size:0.8rem; color:rgba(240,238,255,0.38);
        letter-spacing:0.02em; padding-left:3.1rem;
    ">Intelligent document understanding · Grounded answers · Always accurate</p>
</div>
""", unsafe_allow_html=True)

# ── Tab navigation ─────────────────────────────────────────────────────────────
st.markdown('<div class="anim-2" style="padding: 1.2rem 2.5rem 0;">', unsafe_allow_html=True)
col_tabs, col_spacer = st.columns([3, 7])
with col_tabs:
    t1, t2 = st.columns(2)
    with t1:
        if st.button("💬  Chat", key="tab_chat", use_container_width=True):
            st.session_state.active_tab = "chat"
            st.rerun()
    with t2:
        history_count = len(st.session_state.chat_history)
        label = f"🕘  History ({history_count})" if history_count else "🕘  History"
        if st.button(label, key="tab_history", use_container_width=True):
            st.session_state.active_tab = "history"
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB: CHAT
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.active_tab == "chat":

    # ── Upload section ────────────────────────────────────────────────────────
    st.markdown('<div class="anim-2" style="padding: 0 2.5rem;">', unsafe_allow_html=True)
    render_file_uploader(api_url=BACKEND_URL)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div style="margin:1.2rem 2.5rem;
                height:1px;
                background:linear-gradient(90deg,transparent,rgba(120,100,255,0.2),transparent);">
    </div>
    """, unsafe_allow_html=True)

    # ── Chat messages ─────────────────────────────────────────────────────────
    st.markdown('<div style="padding: 0 2.5rem;">', unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown("""
        <div class="anim-3" style="
            text-align:center; padding: 3rem 2rem;
            color:rgba(240,238,255,0.2);
        ">
            <div style="font-size:3rem; margin-bottom:1rem; opacity:0.4;">◈</div>
            <p style="font-family:'Outfit',sans-serif; font-size:1rem; font-weight:500;
                      color:rgba(240,238,255,0.3);">
                Upload a document and ask anything
            </p>
            <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;
                      color:rgba(240,238,255,0.18); margin-top:0.4rem;">
                or ask any question — DocMind answers from docs or general knowledge
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        for turn in st.session_state.chat_history:
            render_chat_box(
                user_text=turn["user"],
                ai_text=turn["answer"],
                mode=turn.get("mode", "rag"),
            )
            if turn.get("chunks"):
                render_citations(turn["chunks"])
            st.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Clear button ──────────────────────────────────────────────────────────
    if st.session_state.chat_history:
        st.markdown('<div style="padding: 0 2.5rem 0.5rem; text-align:right;">', unsafe_allow_html=True)
        if st.button("🗑  Clear chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.input_key += 1
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Input bar ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="anim-4" style="
        position: sticky; bottom: 0;
        padding: 1rem 2.5rem 1.5rem;
        background: linear-gradient(to top, rgba(7,7,16,1) 60%, transparent);
        margin-top: 1rem;
    ">
    """, unsafe_allow_html=True)

    col_input, col_btn = st.columns([6, 1])
    with col_input:
        user_input = st.text_input(
            label="q",
            placeholder="Ask anything about your documents…",
            label_visibility="collapsed",
            key=f"query_input_{st.session_state.input_key}",
        )
    with col_btn:
        ask_clicked = st.button("Ask ◈", use_container_width=True, key="ask_btn")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Handle query ──────────────────────────────────────────────────────────
    if ask_clicked:
        if not user_input.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner(""):
                st.markdown("""
                <div style="
                    display:flex; align-items:center; gap:0.6rem;
                    padding: 0.6rem 2.5rem;
                    font-family:'JetBrains Mono',monospace;
                    font-size:0.78rem; color:rgba(120,100,255,0.7);
                ">
                    <span class="pulse-dot"></span> Thinking…
                </div>
                """, unsafe_allow_html=True)
                try:
                    response = requests.post(
                        f"{BACKEND_URL}/query",
                        json={"query": user_input},
                        timeout=60,
                    )
                except Exception as e:
                    st.error(f"Backend unreachable: {e}")
                    st.stop()

            if response.status_code != 200:
                st.error(f"Backend error {response.status_code}")
            else:
                data      = response.json()
                answer    = data.get("answer", "No answer returned.")
                chunks    = data.get("chunks", [])
                citations = data.get("citations", [])
                mode      = data.get("mode", "rag")

                st.session_state.chat_history.append({
                    "user":      user_input,
                    "answer":    answer,
                    "citations": citations,
                    "chunks":    chunks,
                    "mode":      mode,
                    "time":      datetime.now().strftime("%d %b %Y, %I:%M %p"),
                })
                st.session_state.input_key += 1
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# TAB: HISTORY
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.active_tab == "history":

    st.markdown('<div style="padding: 0 2.5rem;">', unsafe_allow_html=True)

    if not st.session_state.chat_history:
        st.markdown("""
        <div style="text-align:center; padding:4rem 2rem;">
            <div style="font-size:2.5rem; opacity:0.2; margin-bottom:1rem;">🕘</div>
            <p style="font-family:'Outfit',sans-serif; font-size:1rem;
                      color:rgba(240,238,255,0.25); font-weight:500;">
                No search history yet
            </p>
            <p style="font-family:'JetBrains Mono',monospace; font-size:0.75rem;
                      color:rgba(240,238,255,0.15); margin-top:0.3rem;">
                Your queries will appear here after you ask something
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Header row
        col_title, col_clear = st.columns([5, 1])
        with col_title:
            st.markdown(f"""
            <p style="font-family:'Outfit',sans-serif; font-size:0.75rem; font-weight:600;
                      color:rgba(240,238,255,0.3); letter-spacing:0.1em;
                      text-transform:uppercase; margin-bottom:1rem;">
                {len(st.session_state.chat_history)} queries in history
            </p>
            """, unsafe_allow_html=True)
        with col_clear:
            if st.button("🗑 Clear all", key="clear_history"):
                st.session_state.chat_history = []
                st.rerun()

        # History entries (newest first)
        to_delete = None
        for idx, turn in enumerate(reversed(st.session_state.chat_history)):
            real_idx = len(st.session_state.chat_history) - 1 - idx
            mode_tag = "📄 RAG" if turn.get("mode") == "rag" else "🧠 General"
            mode_color = "#7864ff" if turn.get("mode") == "rag" else "#ff6b9d"
            time_str = turn.get("time", "")

            # Truncate answer preview
            preview = turn["answer"].replace("\n", " ")
            preview = (preview[:160] + "…") if len(preview) > 160 else preview
            # Strip any leading warning emoji lines
            preview = preview.lstrip("⚠️ℹ️").strip()

            st.markdown(f"""
            <div class="history-card" style="animation-delay:{idx * 0.05}s">
                <div style="display:flex; justify-content:space-between;
                            align-items:flex-start; margin-bottom:0.55rem;">
                    <div style="display:flex; align-items:center; gap:0.5rem; flex:1;">
                        <span style="
                            font-family:'JetBrains Mono',monospace;
                            font-size:0.65rem; color:{mode_color};
                            background:rgba(120,100,255,0.08);
                            border:1px solid rgba(120,100,255,0.15);
                            border-radius:99px; padding:0.15rem 0.5rem;
                            white-space:nowrap;
                        ">{mode_tag}</span>
                        <span style="
                            font-family:'Outfit',sans-serif; font-weight:600;
                            font-size:0.95rem; color:rgba(240,238,255,0.9);
                        ">{turn["user"]}</span>
                    </div>
                    <span style="
                        font-family:'JetBrains Mono',monospace;
                        font-size:0.65rem; color:rgba(240,238,255,0.22);
                        white-space:nowrap; margin-left:0.8rem;
                    ">{time_str}</span>
                </div>
                <p style="
                    font-family:'Outfit',sans-serif; font-size:0.82rem;
                    color:rgba(240,238,255,0.45); line-height:1.55;
                    margin:0; padding-left:0.1rem;
                ">{preview}</p>
            </div>
            """, unsafe_allow_html=True)

            col_view, col_del = st.columns([5, 1])
            with col_view:
                if st.button(f"View full answer", key=f"view_{real_idx}",
                             use_container_width=True):
                    st.session_state.active_tab = "chat"
                    # Scroll to this turn by rerunning on chat tab
                    st.rerun()
            with col_del:
                if st.button("🗑", key=f"del_{real_idx}", use_container_width=True):
                    to_delete = real_idx

        if to_delete is not None:
            st.session_state.chat_history.pop(to_delete)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)