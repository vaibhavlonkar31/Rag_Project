# scripts/ui/components/chat_box.py

import re
import streamlit as st


def render_chat_box(
    user_text: str,
    ai_text: str,
    citations: list | None = None,
    chunks: list | None = None,
    mode: str = "rag",
    turn_index: int = 0,
):
    delay = min(turn_index * 0.04, 0.25)

    badge_html = (
        '<span class="badge badge-rag">📄 From Documents</span>'
        if mode == "rag" else
        '<span class="badge badge-general">🌐 General Knowledge</span>'
    )

    # ── User bubble ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        display:flex;justify-content:flex-end;
        margin:.8rem 0 .4rem;
        animation:fadeSlideUp .4s {delay}s ease both;opacity:0;animation-fill-mode:forwards;
    ">
        <div style="
            max-width:72%;
            background:linear-gradient(135deg,rgba(124,111,255,.18),rgba(255,111,145,.12));
            border:1px solid rgba(124,111,255,.25);
            border-radius:18px 18px 4px 18px;
            padding:.85rem 1.15rem;
            font-family:'Outfit',sans-serif;font-size:.95rem;
            color:#f0eeff;line-height:1.55;
            box-shadow:0 4px 20px rgba(124,111,255,.1);
        ">
            <div style="font-family:'JetBrains Mono',monospace;font-size:.58rem;
                        color:rgba(124,111,255,.65);letter-spacing:.08em;
                        text-transform:uppercase;margin-bottom:.35rem;">You</div>
            {user_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── AI label ──────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        display:flex;align-items:center;gap:.5rem;
        margin:.3rem 0 .2rem;
        animation:fadeIn .35s {delay + 0.1}s ease both;opacity:0;animation-fill-mode:forwards;
    ">
        <div style="
            width:26px;height:26px;
            background:linear-gradient(135deg,#7c6fff,#00e5c0);
            border-radius:8px;display:flex;align-items:center;justify-content:center;
            font-size:.75rem;box-shadow:0 2px 10px rgba(124,111,255,.3);flex-shrink:0;
        ">◈</div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:.6rem;
                     color:rgba(240,238,255,.4);letter-spacing:.08em;text-transform:uppercase;">
            DocMind AI</span>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)

    # ── AI answer card ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        background:rgba(14,14,26,.85);
        border:1px solid rgba(255,255,255,.08);
        border-radius:4px 18px 18px 18px;
        padding:1rem 1.2rem;margin-bottom:.5rem;
        backdrop-filter:blur(12px);
        box-shadow:0 4px 30px rgba(0,0,0,.28);
        animation:fadeSlideUp .45s {delay + 0.15}s ease both;
        opacity:0;animation-fill-mode:forwards;
    ">
    """, unsafe_allow_html=True)

    # Clean citation markers from text
    clean_text = re.sub(r'\[CHUNK\s*\d+[^\]]*\]', '', ai_text)
    clean_text = re.sub(r'\[doc_[^\]]+\]', '', clean_text).strip()

    # Split on code blocks
    parts = re.split(r'(```[\w]*\n[\s\S]*?```)', clean_text)
    for part in parts:
        if part.startswith("```"):
            lines = part.strip().split("\n")
            lang  = lines[0].replace("```", "").strip() or "text"
            code  = "\n".join(lines[1:]).rstrip("`").strip()
            st.code(code, language=lang)
        else:
            stripped = part.strip()
            if not stripped:
                continue
            # Convert inline **bold** and bullet lists to HTML
            html = _md_to_html(stripped)
            st.markdown(
                f"<div style='font-family:Outfit,sans-serif;font-size:.93rem;"
                f"color:rgba(240,238,255,.88);line-height:1.72;margin:.15rem 0;'>"
                f"{html}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)


def _md_to_html(text: str) -> str:
    """Convert basic markdown (bold, bullets, newlines) to safe HTML."""
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong style="color:#f0eeff;font-weight:700;">\1</strong>', text)
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code style="font-family:JetBrains Mono,monospace;font-size:.85em;'
                                r'background:rgba(124,111,255,.15);border-radius:5px;'
                                r'padding:.1em .35em;color:#7c6fff;">\1</code>', text)

    lines      = text.split('\n')
    html_lines = []
    for line in lines:
        line_s = line.strip()
        if not line_s:
            html_lines.append('<div style="height:.4rem;"></div>')
        elif re.match(r'^[\*\+\-]\s+', line_s):
            content = re.sub(r'^[\*\+\-]\s+', '', line_s)
            html_lines.append(
                f'<div style="display:flex;gap:.5rem;margin:.2rem 0;align-items:flex-start;">'
                f'<span style="color:#7c6fff;margin-top:.15rem;flex-shrink:0;">▸</span>'
                f'<span>{content}</span></div>'
            )
        elif re.match(r'^\d+\.\s+', line_s):
            m       = re.match(r'^(\d+)\.\s+(.*)', line_s)
            num     = m.group(1) if m else ""
            content = m.group(2) if m else line_s
            html_lines.append(
                f'<div style="display:flex;gap:.5rem;margin:.2rem 0;align-items:flex-start;">'
                f'<span style="color:#7c6fff;font-family:JetBrains Mono,monospace;'
                f'font-size:.8em;margin-top:.1rem;flex-shrink:0;">{num}.</span>'
                f'<span>{content}</span></div>'
            )
        else:
            html_lines.append(f'<div style="margin:.1rem 0;">{line_s}</div>')

    return "\n".join(html_lines)