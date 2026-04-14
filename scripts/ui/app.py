# scripts/ui/app.py  — DocMind AI

import sys
import uuid
from pathlib import Path
from datetime import datetime

import requests
import streamlit as st

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

BACKEND_URL = "http://127.0.0.1:8000"

# ── Session defaults ───────────────────────────────────────────────────────────
for _k, _v in {
    "sessions":       [],
    "active_session": None,
    "input_key":      0,
    "active_section": "chat",
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def _get_session(sid):
    return next((s for s in st.session_state.sessions if s["id"] == sid), None)

def _active_session():
    return _get_session(st.session_state.active_session or "")

def _new_session():
    sess = {
        "id":        str(uuid.uuid4())[:8],
        "title":     "New Chat",
        "timestamp": datetime.now().strftime("%b %d, %H:%M"),
        "turns":     [],
        "summaries": {},
        "section":   st.session_state.get("active_section", "chat"),
    }
    st.session_state.sessions.insert(0, sess)
    st.session_state.active_session = sess["id"]
    st.session_state.input_key += 1
    return sess

def _auto_title(q):
    words = q.strip().split()
    raw = " ".join(words[:7])
    return (raw[:45] + "…") if len(raw) > 45 else raw

if not st.session_state.sessions or _active_session() is None:
    _new_session()


# ══════════════════════════════════════════════════════════════════════════════
# CSS — No sidebar, enhanced animations
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg:#080810; --bg2:#0e0e1a; --bg3:#141428;
  --a1:#7c6fff; --a2:#ff6f91; --a3:#00e5c0;
  --t1:#f0eeff; --t2:rgba(240,238,255,.6); --t3:rgba(240,238,255,.28);
}

/* ── Keyframes ── */
@keyframes fadeUp       { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
@keyframes fadeIn       { from{opacity:0} to{opacity:1} }
@keyframes fadeSlideIn  { from{opacity:0;transform:translateX(-12px)} to{opacity:1;transform:translateX(0)} }
@keyframes orb          { 0%,100%{transform:translateY(0) scale(1)} 50%{transform:translateY(-30px) scale(1.06)} }
@keyframes orbRight     { 0%,100%{transform:translateY(0) rotate(0deg)} 50%{transform:translateY(22px) rotate(8deg)} }
@keyframes gShift       { 0%,100%{background-position:0% 50%} 50%{background-position:100% 50%} }
@keyframes bGlow        { 0%,100%{border-color:rgba(124,111,255,.25)} 50%{border-color:rgba(0,229,192,.45)} }
@keyframes pulse        { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.85)} }
@keyframes shimmer      { 0%{background-position:-400px 0} 100%{background-position:400px 0} }
@keyframes titleGlow    { 0%,100%{text-shadow:0 0 20px rgba(124,111,255,.3)} 50%{text-shadow:0 0 35px rgba(0,229,192,.4)} }
@keyframes scanLine     { 0%{top:-20%} 100%{top:120%} }
@keyframes hueRotate    { 0%{filter:hue-rotate(0deg)} 100%{filter:hue-rotate(360deg)} }
@keyframes borderPulse  { 0%,100%{box-shadow:0 0 0 0 rgba(124,111,255,.2)} 50%{box-shadow:0 0 0 6px rgba(124,111,255,0)} }
@keyframes floatBadge   { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-3px)} }

*,*::before,*::after { box-sizing:border-box; }

html,body,[data-testid="stAppViewContainer"] {
    background:var(--bg) !important;
    color:var(--t1) !important;
    font-family:'Outfit',sans-serif !important;
}

/* Kill ALL native Streamlit chrome + sidebar */
footer,#MainMenu,[data-testid="stHeader"],
[data-testid="stToolbar"],[data-testid="stDecoration"],
[data-testid="stSidebarNav"],[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"] { display:none !important; }

/* ── Ambient orbs (enhanced) ── */
[data-testid="stAppViewContainer"]::before {
    content:'';position:fixed;top:-180px;left:80px;
    width:620px;height:620px;border-radius:50%;pointer-events:none;z-index:0;
    background:radial-gradient(circle,rgba(124,111,255,.09) 0%,transparent 68%);
    animation:orb 16s ease-in-out infinite;
}
[data-testid="stAppViewContainer"]::after {
    content:'';position:fixed;bottom:-160px;right:-100px;
    width:520px;height:520px;border-radius:50%;pointer-events:none;z-index:0;
    background:radial-gradient(circle,rgba(0,229,192,.07) 0%,transparent 65%);
    animation:orbRight 20s ease-in-out infinite;
}

/* ── Subtle scan-line shimmer overlay ── */
[data-testid="stMainBlockContainer"]::before {
    content:'';position:fixed;left:0;right:0;height:2px;
    background:linear-gradient(90deg,transparent,rgba(124,111,255,.18),rgba(0,229,192,.12),transparent);
    pointer-events:none;z-index:999;
    animation:scanLine 9s linear infinite;
    opacity:.55;
}

/* Main area */
section.main>div { padding:1.2rem 2.2rem 2.5rem !important; position:relative; z-index:1; }

/* ── Inputs (enhanced) ── */
[data-testid="stTextInput"] input {
    background:var(--bg2) !important;
    border:1.5px solid rgba(124,111,255,.22) !important;
    border-radius:16px !important; color:var(--t1) !important;
    font-family:'JetBrains Mono',monospace !important; font-size:.92rem !important;
    padding:.85rem 1.2rem !important;
    transition:all .35s cubic-bezier(.4,0,.2,1) !important;
    animation:bGlow 6s ease-in-out infinite !important;
}
[data-testid="stTextInput"] input:focus {
    border-color:var(--a1) !important;
    box-shadow:0 0 0 4px rgba(124,111,255,.12),0 4px 20px rgba(124,111,255,.1) !important;
    background:var(--bg3) !important;
}
[data-testid="stTextInput"] input::placeholder { color:var(--t3) !important; }

/* ── Main content buttons (enhanced) ── */
[data-testid="stMainBlockContainer"] [data-testid="stButton"]>button {
    background:linear-gradient(135deg,var(--a1),var(--a2),var(--a3)) !important;
    background-size:250% 250% !important; color:#fff !important;
    border:none !important; border-radius:14px !important;
    font-family:'Outfit',sans-serif !important; font-weight:700 !important;
    font-size:.87rem !important; padding:.65rem 1.2rem !important;
    transition:all .3s cubic-bezier(.4,0,.2,1) !important;
    animation:gShift 4s ease infinite !important;
    box-shadow:0 4px 18px rgba(124,111,255,.26) !important;
    cursor:pointer !important; position:relative !important; overflow:hidden !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stButton"]>button::after {
    content:'';position:absolute;top:0;left:-100%;width:100%;height:100%;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,.12),transparent);
    transition:left .4s ease !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stButton"]>button:hover::after {
    left:100%;
}
[data-testid="stMainBlockContainer"] [data-testid="stButton"]>button:hover {
    transform:translateY(-3px) scale(1.03) !important;
    box-shadow:0 10px 28px rgba(124,111,255,.42) !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stButton"]>button[kind="secondary"] {
    background:rgba(255,255,255,.05) !important;
    border:1px solid rgba(255,255,255,.1) !important;
    box-shadow:none !important; animation:none !important;
    color:rgba(240,238,255,.6) !important;
}
[data-testid="stMainBlockContainer"] [data-testid="stButton"]>button[kind="secondary"]:hover {
    background:rgba(255,255,255,.09) !important;
    border-color:rgba(255,255,255,.2) !important;
    color:var(--t1) !important;
    transform:translateY(-1px) !important;
}

/* ── Section nav tabs ── */
.section-tabs {
    display:flex; gap:.55rem; margin:.6rem 0 1.1rem;
    animation:fadeUp .5s .05s ease both;
}
.section-tab {
    display:inline-flex; align-items:center; gap:.35rem;
    padding:.38rem .85rem; border-radius:99px;
    font-family:'Outfit',sans-serif; font-size:.78rem; font-weight:600;
    cursor:pointer; border:1px solid transparent;
    transition:all .25s cubic-bezier(.4,0,.2,1);
    animation:floatBadge 4s ease-in-out infinite;
    text-decoration:none;
}
.section-tab:nth-child(2){ animation-delay:.3s; }
.section-tab:nth-child(3){ animation-delay:.6s; }
.section-tab:nth-child(4){ animation-delay:.9s; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background:var(--bg2) !important;
    border:1.5px dashed rgba(124,111,255,.28) !important;
    border-radius:16px !important; padding:.7rem !important;
    transition:all .3s ease !important;
    animation:bGlow 7s ease-in-out infinite !important;
}
[data-testid="stFileUploader"]:hover {
    border-color:rgba(0,229,192,.5) !important;
    box-shadow:0 0 18px rgba(0,229,192,.08) !important;
}
[data-testid="stFileUploadDropzone"] { background:transparent !important; }
[data-testid="stFileUploadDropzone"] p,
[data-testid="stFileUploadDropzone"] small {
    color:rgba(240,238,255,.4) !important;
    font-family:'JetBrains Mono',monospace !important; font-size:.77rem !important;
}
[data-testid="stFileUploadDropzone"] button {
    background:rgba(124,111,255,.14) !important;
    border:1px solid rgba(124,111,255,.3) !important; color:#7c6fff !important;
    border-radius:8px !important; font-size:.78rem !important;
    font-family:'Outfit',sans-serif !important; padding:.35rem .9rem !important;
    transition:all .2s !important;
}
[data-testid="stFileUploadDropzone"] button:hover {
    background:rgba(124,111,255,.28) !important;
    box-shadow:0 2px 10px rgba(124,111,255,.2) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background:rgba(14,14,26,.7) !important;
    border:1px solid rgba(255,255,255,.07) !important;
    border-radius:14px !important; overflow:hidden !important;
    transition:border-color .3s !important;
}
[data-testid="stExpander"]:hover { border-color:rgba(124,111,255,.22) !important; }
[data-testid="stExpander"] summary {
    color:rgba(240,238,255,.68) !important;
    font-family:'Outfit',sans-serif !important; font-size:.88rem !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb {
    background:linear-gradient(var(--a1),var(--a3));
    border-radius:99px;
}

/* ── Badges ── */
.badge { display:inline-block; padding:.13rem .55rem; border-radius:99px;
    font-family:'JetBrains Mono',monospace; font-size:.58rem;
    letter-spacing:.05em; font-weight:500; vertical-align:middle; }
.badge-rag     { background:rgba(0,229,192,.1);   color:#00e5c0; border:1px solid rgba(0,229,192,.25); }
.badge-general { background:rgba(124,111,255,.1); color:#7c6fff; border:1px solid rgba(124,111,255,.25); }

/* ── Warning / Error ── */
[data-testid="stAlert"] {
    border-radius:12px !important;
    animation:fadeUp .3s ease both !important;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════
SECTIONS = [
    {"key": "chat",      "icon": "💬", "label": "Chat",      "color": "#7c6fff",  "bg": "rgba(124,111,255,.12)", "border": "rgba(124,111,255,.35)"},
    {"key": "docvault",  "icon": "📂", "label": "DocVault",  "color": "#00e5c0",  "bg": "rgba(0,229,192,.1)",   "border": "rgba(0,229,192,.32)"},
    {"key": "codeforge", "icon": "⚡", "label": "CodeForge", "color": "#ff6f91",  "bg": "rgba(255,111,145,.1)", "border": "rgba(255,111,145,.32)"},
    {"key": "oracle",    "icon": "🔮", "label": "Oracle",    "color": "#ffb347",  "bg": "rgba(255,179,71,.1)",  "border": "rgba(255,179,71,.28)"},
]
SECTION_MAP = {s["key"]: s for s in SECTIONS}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
active_section = st.session_state.active_section
sess = _active_session()
if sess is None:
    sess = _new_session()

turns = sess.get("turns", [])
sc_info = SECTION_MAP.get(active_section, SECTION_MAP["chat"])
sc = sc_info["color"]
si = sc_info["icon"]

# ── Top bar: logo + title + live indicator ────────────────────────────────────
col_logo, col_title, col_live = st.columns([0.7, 5, 1])

with col_logo:
    st.markdown("""
    <div style="display:flex;align-items:center;height:42px;">
        <div style="width:34px;height:34px;flex-shrink:0;
            background:linear-gradient(135deg,#7c6fff,#00e5c0);border-radius:10px;
            display:flex;align-items:center;justify-content:center;
            font-size:.9rem;box-shadow:0 3px 14px rgba(124,111,255,.35);
            animation:borderPulse 3s ease-in-out infinite;">◈</div>
    </div>
    """, unsafe_allow_html=True)

with col_title:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:.9rem;height:52px;
                animation:fadeSlideIn .4s ease both;">
        <div>
            <div style="font-family:'Outfit',sans-serif;font-weight:800;font-size:1.45rem;
                        color:#f0eeff;letter-spacing:-.01em;line-height:1.1;">
                Doc<span style="
                    background:linear-gradient(90deg,#7c6fff,#00e5c0);
                    background-size:200%;
                    -webkit-background-clip:text;
                    -webkit-text-fill-color:transparent;
                    background-clip:text;
                    animation:gShift 5s ease infinite;">Mind</span>
                <span style="font-size:.75rem;font-weight:500;
                    color:rgba(240,238,255,.35);margin-left:.3rem;
                    font-family:'JetBrains Mono',monospace;
                    -webkit-text-fill-color:rgba(240,238,255,.35);">AI</span>
            </div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:.54rem;
                        color:rgba(240,238,255,.22);margin-top:.15rem;display:flex;align-items:center;gap:.4rem;">
                <span style="color:{sc};opacity:.8;">{si} {sess['title']}</span>
                <span style="opacity:.4;">·</span>
                <span>{sess['timestamp']}</span>
                <span style="opacity:.4;">·</span>
                <span>{len(turns)} msg</span>
                <span style="opacity:.4;">·</span>
                <span style="color:{sc};opacity:.7;">{active_section.upper()}</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_live:
    st.markdown("""
    <div style="display:flex;align-items:center;justify-content:flex-end;
                gap:.4rem;height:42px;">
        <div style="width:8px;height:8px;background:#00e5c0;border-radius:50%;
                    animation:pulse 2s ease-in-out infinite;
                    box-shadow:0 0 10px rgba(0,229,192,.65);"></div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:.57rem;
                     color:rgba(0,229,192,.72);letter-spacing:.08em;">LIVE</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='border-top:1px solid rgba(255,255,255,.07);margin:.45rem 0 .7rem;'></div>",
            unsafe_allow_html=True)

# ── Section nav tabs (inline, no sidebar needed) ──────────────────────────────
tab_cols = st.columns(len(SECTIONS) + 2)
for i, sec in enumerate(SECTIONS):
    with tab_cols[i]:
        is_active = sec["key"] == active_section
        btn_style = "primary" if is_active else "secondary"
        if st.button(
            f"{sec['icon']} {sec['label']}",
            key=f"tab_{sec['key']}",
            use_container_width=True,
            type=btn_style,
        ):
            st.session_state.active_section = sec["key"]
            sec_sessions = [s for s in st.session_state.sessions
                            if s.get("section") == sec["key"]]
            if sec_sessions:
                st.session_state.active_session = sec_sessions[0]["id"]
            else:
                _new_session()
            st.rerun()

with tab_cols[len(SECTIONS)]:
    if st.button("＋ New Chat", key="btn_new_top", use_container_width=True, type="secondary"):
        _new_session()
        st.rerun()

st.markdown("<div style='margin:.6rem 0 .9rem;border-top:1px solid rgba(255,255,255,.05);'></div>",
            unsafe_allow_html=True)

# ── File uploader ──────────────────────────────────────────────────────────────
render_file_uploader(api_url=BACKEND_URL, session=sess)
st.markdown("<div style='margin:.85rem 0;border-top:1px solid rgba(255,255,255,.05);'></div>",
            unsafe_allow_html=True)

# ── Chat turns / empty state ───────────────────────────────────────────────────
if not turns:
    EMPTY = {
        "chat": {
            "icon": "💬", "heading": "Ask me anything",
            "body": "General conversation powered by LLaMA 3. No documents needed.",
        },
        "docvault": {
            "icon": "📂", "heading": "Query your documents",
            "body": "Upload a PDF, DOCX or TXT above, then ask questions. DocVault retrieves and cites the exact sources.",
        },
        "codeforge": {
            "icon": "⚡", "heading": "Write. Debug. Refactor.",
            "body": "Describe code you need, paste a snippet to fix, or ask for an explanation. Powered by LLaMA 3.",
        },
        "oracle": {
            "icon": "🔮", "heading": "Deep knowledge, instant answers",
            "body": "Ask complex multi-step questions. Oracle combines your documents with broad world knowledge.",
        },
    }
    e = EMPTY.get(active_section, EMPTY["chat"])
    st.markdown(f"""
    <div style="text-align:center;padding:3rem 1rem 2rem;
                animation:fadeUp .55s .1s ease both;opacity:0;animation-fill-mode:forwards;">
        <div style="font-size:2.8rem;margin-bottom:.9rem;
                    filter:drop-shadow(0 0 28px {sc}80);
                    animation:orb 5s ease-in-out infinite;">{e['icon']}</div>
        <div style="font-family:'Outfit',sans-serif;font-size:1.05rem;font-weight:700;
                    color:rgba(240,238,255,.72);margin-bottom:.45rem;
                    animation:fadeUp .55s .25s ease both;opacity:0;animation-fill-mode:forwards;">
            {e['heading']}</div>
        <div style="font-family:'Outfit',sans-serif;font-size:.83rem;
                    color:rgba(240,238,255,.28);max-width:380px;margin:0 auto;line-height:1.7;
                    animation:fadeUp .55s .4s ease both;opacity:0;animation-fill-mode:forwards;">
            {e['body']}</div>
        <div style="display:flex;gap:.55rem;justify-content:center;margin-top:1.4rem;flex-wrap:wrap;
                    animation:fadeUp .55s .55s ease both;opacity:0;animation-fill-mode:forwards;">
            <span class="badge badge-general" style="animation:floatBadge 3.5s ease-in-out infinite;">📂 DocVault</span>
            <span class="badge badge-rag" style="animation:floatBadge 3.5s ease-in-out infinite .4s;">⚡ CodeForge</span>
            <span style="background:rgba(255,111,145,.08);border:1px solid rgba(255,111,145,.22);
                border-radius:99px;padding:.13rem .55rem;font-family:'JetBrains Mono',monospace;
                font-size:.58rem;color:#ff6f91;
                animation:floatBadge 3.5s ease-in-out infinite .8s;">🔮 Oracle</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for i, turn in enumerate(turns):
        render_chat_box(
            user_text=turn["user"],
            ai_text=turn["answer"],
            citations=turn.get("citations", []),
            chunks=turn.get("chunks", []),
            mode=turn.get("mode", "rag"),
            turn_index=i,
        )
        if turn.get("chunks"):
            render_citations(turn["chunks"])

    col_clr, _ = st.columns([1, 6])
    with col_clr:
        if st.button("🗑 Clear", key="clear_main", type="secondary"):
            sess["turns"] = []
            sess["title"] = "New Chat"
            sess["summaries"] = {}
            st.session_state.input_key += 1
            st.rerun()

# ── Input bar ──────────────────────────────────────────────────────────────────
st.markdown("""
<p style="font-family:'Outfit',sans-serif;font-size:.67rem;font-weight:600;
           color:rgba(240,238,255,.22);letter-spacing:.1em;text-transform:uppercase;
           margin:.85rem 0 .38rem;animation:fadeIn .4s ease both;">Ask Anything</p>
""", unsafe_allow_html=True)

col_i, col_b = st.columns([5, 1])
with col_i:
    user_input = st.text_input(
        label="q",
        placeholder="Ask about your documents, write code, or anything…",
        label_visibility="collapsed",
        key=f"q_{st.session_state.input_key}",
    )
with col_b:
    ask = st.button("Send ➤", use_container_width=True, key="send_main")

if ask:
    if not user_input.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking…"):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/query",
                    json={"query": user_input},
                    timeout=90,
                )
            except Exception as e:
                st.error(f"Could not reach backend: {e}")
                st.stop()

        if resp.status_code != 200:
            st.error(f"Backend error {resp.status_code}: {resp.text}")
        else:
            d = resp.json()
            turn = {
                "user":      user_input,
                "answer":    d.get("answer", "No answer returned."),
                "citations": d.get("citations", []),
                "chunks":    d.get("chunks", []),
                "mode":      d.get("mode", "rag"),
                "timestamp": datetime.now().strftime("%H:%M"),
            }
            sess["turns"].append(turn)
            if len(sess["turns"]) == 1:
                sess["title"] = _auto_title(user_input)
            st.session_state.input_key += 1
            st.rerun()