# scripts/ui/components/citations_viewer.py

import streamlit as st


def render_citations(chunks: list):
    """Render retrieved document chunks as clean expandable source cards."""
    if not chunks:
        return

    valid = []
    for c in chunks:
        text = c.get("text", "") if isinstance(c, dict) else str(c)
        text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t ").strip()
        if text:
            valid.append((c, text))

    if not valid:
        return

    st.markdown(f"""
    <div style="margin-top:.3rem;animation:fadeIn .5s .3s ease both;
                opacity:0;animation-fill-mode:forwards;">
        <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.6rem;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:.63rem;
                         color:rgba(240,238,255,.28);letter-spacing:.1em;text-transform:uppercase;">
                📎 {len(valid)} Source{'s' if len(valid)!=1 else ''}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for i, (chunk, text) in enumerate(valid):
        if isinstance(chunk, dict):
            source = chunk.get("source_file", chunk.get("title", f"Source {i+1}"))
            score  = chunk.get("final_score", chunk.get("score"))
        else:
            source = f"Source {i + 1}"
            score  = None

        score_html = ""
        if score is not None:
            pct   = int(float(score) * 100)
            color = "#00e5c0" if pct >= 60 else "#ff6f91" if pct < 35 else "#7c6fff"
            score_html = f"""
            <span style="font-family:'JetBrains Mono',monospace;font-size:.63rem;
                color:{color};background:rgba(0,0,0,.3);
                border:1px solid {color}40;
                border-radius:99px;padding:.1rem .5rem;">{pct}% match</span>"""

        with st.expander(f"📄  {source}", expanded=False):
            st.markdown(f"""
            <div style="font-family:'JetBrains Mono',monospace;
                font-size:.8rem;color:rgba(240,238,255,.65);
                line-height:1.75;padding:.3rem 0;
                border-left:2px solid rgba(124,111,255,.3);
                padding-left:.8rem;">{text}</div>
            {score_html}
            """, unsafe_allow_html=True)