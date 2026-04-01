# scripts/ui/components/chat_box.py

import streamlit as st
import re


def show_user_message(text: str):
    st.markdown(f"""
    <div style="
        display:flex; justify-content:flex-end;
        margin: 0.8rem 0 0.4rem;
        animation: fadeSlideUp 0.35s ease both;
    ">
        <div style="
            max-width: 70%;
            background: linear-gradient(135deg,
                rgba(120,100,255,0.18) 0%,
                rgba(155,109,255,0.12) 100%);
            border: 1px solid rgba(120,100,255,0.3);
            border-radius: 18px 18px 4px 18px;
            padding: 0.75rem 1.1rem;
            font-family: 'Outfit', sans-serif;
            font-size: 0.93rem;
            color: rgba(240,238,255,0.92);
            line-height: 1.55;
            box-shadow: 0 4px 20px rgba(120,100,255,0.1);
        ">
            <span style="
                font-size: 0.6rem;
                font-family: 'JetBrains Mono', monospace;
                color: rgba(120,100,255,0.7);
                letter-spacing: 0.1em;
                text-transform: uppercase;
                display: block;
                margin-bottom: 0.3rem;
            ">You</span>
            {text}
        </div>
    </div>
    """, unsafe_allow_html=True)


def show_ai_message(ai_text: str, mode: str = "rag"):
    """
    Render AI response cleanly — no chunk labels, no citations noise.
    Code blocks get syntax highlighting via st.code().
    """
    # Strip leading mode-prefix lines (⚠️ / ℹ️) — render them separately as badge
    prefix_badge = ""
    clean_text   = ai_text

    if ai_text.startswith("⚠️"):
        lines      = ai_text.split("\n", 2)
        prefix_badge = lines[0].replace("⚠️", "").strip()
        clean_text   = "\n".join(lines[2:]) if len(lines) > 2 else ""
    elif ai_text.startswith("ℹ️"):
        lines        = ai_text.split("\n", 2)
        prefix_badge = lines[0].replace("ℹ️", "").strip()
        clean_text   = "\n".join(lines[2:]) if len(lines) > 2 else ""

    # Also strip any "[CHUNK X | source: ...]" labels the LLM may echo
    clean_text = re.sub(r'\[CHUNK\s*\d+[^\]]*\]', '', clean_text)
    # Strip citation refs like [doc_xxx]
    clean_text = re.sub(r'\[doc_[^\]]+\]', '', clean_text)
    clean_text = clean_text.strip()

    # Accent color based on mode
    accent = "#7864ff" if mode == "rag" else "#ff6b9d"
    label  = "◈ DocMind · Document" if mode == "rag" else "◈ DocMind · General"

    # Badge for fallback mode
    badge_html = ""
    if prefix_badge:
        badge_html = f"""
        <div style="
            display:inline-flex; align-items:center; gap:0.4rem;
            font-family:'JetBrains Mono',monospace; font-size:0.7rem;
            color:#ff6b9d;
            background:rgba(255,107,157,0.08);
            border:1px solid rgba(255,107,157,0.2);
            border-radius:8px; padding:0.3rem 0.7rem;
            margin-bottom:0.6rem;
        ">ℹ {prefix_badge}</div>"""

    # Split on fenced code blocks
    parts = re.split(r"(```[\w]*\n[\s\S]*?```)", clean_text)

    # Label
    st.markdown(f"""
    <div style="
        display:flex; align-items:center; gap:0.5rem;
        margin: 0.5rem 0 0.25rem;
        animation: fadeSlideUp 0.35s 0.05s ease both;
    ">
        <div style="
            width:26px; height:26px;
            background: linear-gradient(135deg, {accent}, #9b6dff);
            border-radius:8px;
            display:flex; align-items:center; justify-content:center;
            font-size:0.7rem; color:#fff;
            box-shadow: 0 2px 10px rgba(120,100,255,0.3);
        ">◈</div>
        <span style="
            font-family:'JetBrains Mono',monospace; font-size:0.63rem;
            color:{accent}; letter-spacing:0.08em; text-transform:uppercase;
        ">{label}</span>
    </div>
    """, unsafe_allow_html=True)

    # Message card opens
    st.markdown(f"""
    <div style="
        background: rgba(14,14,26,0.8);
        border: 1px solid rgba(120,100,255,0.12);
        border-left: 2px solid {accent};
        border-radius: 4px 18px 18px 18px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        font-family: 'Outfit', sans-serif;
        font-size: 0.92rem;
        color: rgba(240,238,255,0.88);
        line-height: 1.7;
        box-shadow: 0 4px 24px rgba(0,0,0,0.2);
        animation: fadeSlideUp 0.4s 0.08s ease both;
    ">
    {badge_html}
    """, unsafe_allow_html=True)

    # Render each part
    for part in parts:
        if part.startswith("```"):
            lines = part.strip().split("\n")
            lang  = lines[0].replace("```", "").strip() or "text"
            code  = "\n".join(lines[1:]).rstrip("`").strip()
            st.code(code, language=lang)
        else:
            if part.strip():
                formatted = part.replace("\n", "<br>")
                st.markdown(
                    f"<div style='margin:0.2rem 0;'>{formatted}</div>",
                    unsafe_allow_html=True,
                )

    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_box(
    user_text: str,
    ai_text: str,
    citations: list | None = None,
    chunks: list | None = None,
    mode: str = "rag",
):
    show_user_message(user_text)
    show_ai_message(ai_text, mode=mode)