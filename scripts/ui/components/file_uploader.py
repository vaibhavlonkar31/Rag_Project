# scripts/ui/components/file_uploader.py

import re
import requests
import streamlit as st


def render_file_uploader(api_url: str, session: dict | None = None):
    """
    session["summaries"] stores {filename: summary_text}.
    Rule: summaries are ONLY rendered from session["summaries"].
    _explain_files() saves to session but does NOT call _render_summary_card().
    This function renders them once at the end — no duplicates ever.
    """

    st.markdown("""
    <p style="font-family:'Outfit',sans-serif;font-size:.69rem;font-weight:600;
               color:rgba(240,238,255,.24);letter-spacing:.1em;
               text-transform:uppercase;margin-bottom:.45rem;">Upload Documents</p>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        label="Drop files",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded_files:
        # Even with no files selected, still show existing summaries for this session
        if session and session.get("summaries"):
            for fname, summary in session["summaries"].items():
                _render_summary_card(fname, summary)
        return

    names = ", ".join(f.name for f in uploaded_files)
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:.5rem;
                font-family:'JetBrains Mono',monospace;font-size:.76rem;
                color:rgba(0,229,192,.75);margin:.35rem 0 .65rem;">
        <span>📄</span><span>{names}</span>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        do_index   = st.button("⬆ Index",           use_container_width=True, key="btn_idx")
    with col2:
        do_explain = st.button("📖 Explain",          use_container_width=True, key="btn_exp")
    with col3:
        do_both    = st.button("✨ Index + Explain",  use_container_width=True, key="btn_both")

    if do_index or do_both:
        _index_files(uploaded_files, api_url)

    if do_explain or do_both:
        # Saves new summaries into session["summaries"] — does NOT render them here
        _fetch_and_save_summaries(uploaded_files, api_url, session)

    # ── Single render point — always exactly once per summary ─────────────────
    if session and session.get("summaries"):
        for fname, summary in session["summaries"].items():
            _render_summary_card(fname, summary)


# ── Index ──────────────────────────────────────────────────────────────────────
def _index_files(uploaded_files, api_url: str):
    success, failed = [], []
    bar = st.progress(0, text="Indexing…")
    for i, f in enumerate(uploaded_files):
        try:
            r = requests.post(
                f"{api_url}/upload",
                files={"file": (f.name, f.getvalue(), f.type)},
                timeout=120,
            )
            (success if r.status_code == 200 else failed).append(f.name)
        except Exception as e:
            failed.append(f"{f.name} ({e})")
        bar.progress((i + 1) / len(uploaded_files), text=f"{i+1}/{len(uploaded_files)} indexed")
    bar.empty()

    if success:
        st.markdown(
            f"<div style='background:rgba(0,229,192,.06);border:1px solid rgba(0,229,192,.22);"
            f"border-radius:11px;padding:.55rem .95rem;margin-top:.35rem;"
            f"font-family:JetBrains Mono,monospace;font-size:.78rem;color:#00e5c0;'>"
            f"✓ Indexed: {', '.join(success)}</div>",
            unsafe_allow_html=True,
        )
    if failed:
        st.markdown(
            f"<div style='background:rgba(255,111,145,.06);border:1px solid rgba(255,111,145,.22);"
            f"border-radius:11px;padding:.55rem .95rem;margin-top:.35rem;"
            f"font-family:JetBrains Mono,monospace;font-size:.78rem;color:#ff6f91;'>"
            f"✗ Failed: {', '.join(failed)}</div>",
            unsafe_allow_html=True,
        )


# ── Fetch summaries and SAVE only — no rendering here ─────────────────────────
def _fetch_and_save_summaries(uploaded_files, api_url: str, session: dict | None):
    if session is None:
        return

    if "summaries" not in session:
        session["summaries"] = {}

    for f in uploaded_files:
        # Skip files already summarised
        if f.name in session["summaries"]:
            continue

        with st.spinner(f"Summarising '{f.name}'…"):
            try:
                r = requests.post(
                    f"{api_url}/summarize",
                    files={"file": (f.name, f.getvalue(), f.type)},
                    timeout=180,
                )
            except Exception as e:
                st.error(f"Backend error for '{f.name}': {e}")
                continue

        if r.status_code != 200:
            st.error(f"Summarisation failed for '{f.name}': {r.text}")
            continue

        # Store — rendering happens once at the bottom of render_file_uploader()
        session["summaries"][f.name] = r.json().get("summary", "No summary returned.")


# ── Parse helpers ──────────────────────────────────────────────────────────────
def _parse_summary(text: str) -> tuple[str, list[str]]:
    def bold(s: str) -> str:
        return re.sub(
            r'\*\*(.*?)\*\*',
            r'<strong style="color:#f0eeff;font-weight:700;">\1</strong>',
            s,
        )

    heading = ""
    bullets = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if re.match(r'^[\*\+\-•]\s+', line):
            bullets.append(bold(re.sub(r'^[\*\+\-•]\s+', '', line)))
        elif re.match(r'^\d+\.\s+', line):
            bullets.append(bold(re.sub(r'^\d+\.\s+', '', line)))
        else:
            clean = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
            if not heading and len(clean) < 80:
                heading = clean
            else:
                bullets.append(bold(line))
    return heading, bullets


def _render_summary_card(filename: str, summary: str):
    heading, bullets = _parse_summary(summary)

    bullet_html = "".join(
        f'<div style="display:flex;gap:.6rem;margin:.38rem 0;align-items:flex-start;">'
        f'<span style="color:#7c6fff;font-size:.82rem;margin-top:.06rem;flex-shrink:0;">▸</span>'
        f'<span style="font-family:Outfit,sans-serif;font-size:.87rem;'
        f'color:rgba(240,238,255,.82);line-height:1.6;">{b}</span></div>'
        for b in bullets
    ) if bullets else (
        f'<p style="font-family:Outfit,sans-serif;font-size:.87rem;'
        f'color:rgba(240,238,255,.75);line-height:1.65;">{summary}</p>'
    )

    heading_html = (
        f'<div style="padding:.85rem 1.25rem .15rem;font-family:Outfit,sans-serif;'
        f'font-weight:700;font-size:.98rem;color:#f0eeff;">{heading}</div>'
        if heading else ""
    )

    st.markdown(f"""
    <div style="
        background:linear-gradient(135deg,rgba(124,111,255,.07),rgba(0,229,192,.04));
        border:1px solid rgba(124,111,255,.2);border-radius:18px;
        padding:0 0 1.1rem;margin:1rem 0;overflow:hidden;
        box-shadow:0 8px 30px rgba(0,0,0,.28);">
        <div style="background:linear-gradient(135deg,rgba(124,111,255,.14),rgba(0,229,192,.07));
                    border-bottom:1px solid rgba(124,111,255,.14);
                    padding:.85rem 1.25rem;display:flex;align-items:center;gap:.65rem;">
            <div style="width:30px;height:30px;flex-shrink:0;
                background:linear-gradient(135deg,#7c6fff,#00e5c0);border-radius:8px;
                display:flex;align-items:center;justify-content:center;
                font-size:.85rem;box-shadow:0 3px 10px rgba(124,111,255,.3);">📄</div>
            <div>
                <div style="font-family:Outfit,sans-serif;font-weight:700;
                            font-size:.93rem;color:#f0eeff;">{filename}</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:.58rem;
                            color:rgba(240,238,255,.3);letter-spacing:.06em;
                            text-transform:uppercase;margin-top:.08rem;">AI Document Summary</div>
            </div>
            <div style="margin-left:auto;">
                <span style="background:rgba(124,111,255,.14);border:1px solid rgba(124,111,255,.28);
                             border-radius:99px;padding:.18rem .65rem;
                             font-family:'JetBrains Mono',monospace;font-size:.6rem;
                             color:#7c6fff;letter-spacing:.05em;">SUMMARY</span>
            </div>
        </div>
        {heading_html}
        <div style="padding:.55rem 1.25rem 0;">{bullet_html}</div>
    </div>
    """, unsafe_allow_html=True)