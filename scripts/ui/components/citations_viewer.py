# scripts/ui/components/citations_viewer.py

import streamlit as st


def render_citations(chunks: list):
    """Render retrieved chunks as collapsible source cards. UUIDs hidden."""
    if not chunks:
        return

    st.markdown("""
    <p style="
        font-family:'JetBrains Mono',monospace;
        font-size:0.65rem; font-weight:500;
        color:rgba(240,238,255,0.25);
        letter-spacing:0.1em; text-transform:uppercase;
        margin: 0.2rem 0 0.5rem 0.1rem;
    ">▸ Source Excerpts</p>
    """, unsafe_allow_html=True)

    for i, chunk in enumerate(chunks):
        # Normalize — chunk can be str or dict
        if isinstance(chunk, dict):
            text   = chunk.get("text", "")
            source = chunk.get("source_file") or chunk.get("source") or chunk.get("title", "")
            score  = chunk.get("final_score") or chunk.get("score")
        else:
            text   = str(chunk)
            source = ""
            score  = None

        # Clean text
        text = "".join(c for c in text if c.isprintable() or c in "\n\t ").strip()

        # Build label — use source filename, not UUID
        label_parts = [f"Source {i + 1}"]
        if source:
            label_parts.append(source)
        if score is not None:
            pct = int(float(score) * 100)
            label_parts.append(f"{pct}% match")
        label = " · ".join(label_parts)

        with st.expander(label, expanded=False):
            if text:
                st.markdown(f"""
                <div style="
                    font-family:'JetBrains Mono',monospace;
                    font-size:0.8rem;
                    color:rgba(240,238,255,0.6);
                    line-height:1.75;
                    padding:0.2rem 0;
                    white-space:pre-wrap;
                ">{text}</div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(
                    "<em style='color:rgba(240,238,255,0.2); font-size:0.8rem;'>"
                    "No text available.</em>",
                    unsafe_allow_html=True,
                )