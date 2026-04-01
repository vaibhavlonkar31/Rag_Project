# scripts/ui/components/file_uploader.py

import streamlit as st
import requests
import re


def render_file_uploader(api_url: str):
    """Render the document upload panel."""

    st.markdown("""
    <p style="
        font-family:'JetBrains Mono',monospace;
        font-size:0.65rem; font-weight:500;
        color:rgba(240,238,255,0.28);
        letter-spacing:0.1em; text-transform:uppercase;
        margin-bottom:0.5rem;
    ">Upload Documents</p>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        label="drop",
        type=["pdf", "txt", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded_files:
        return

    names = "  ·  ".join(f.name for f in uploaded_files)
    st.markdown(f"""
    <p style="
        font-family:'JetBrains Mono',monospace; font-size:0.78rem;
        color:rgba(0,212,170,0.7); margin:0.3rem 0 0.7rem;
    ">📄 {names}</p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        do_index = st.button("Index ↑", use_container_width=True, key="btn_index")
    with col2:
        do_explain = st.button("Explain 📖", use_container_width=True, key="btn_explain")
    with col3:
        do_both = st.button("Index + Explain ✨", use_container_width=True, key="btn_both")

    if do_index or do_both:
        _index_files(uploaded_files, api_url)
    if do_explain or do_both:
        _explain_files(uploaded_files, api_url)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _index_files(files, api_url: str):
    success, failed = [], []
    bar = st.progress(0, text="Indexing…")
    for i, f in enumerate(files):
        try:
            r = requests.post(
                f"{api_url}/upload",
                files={"file": (f.name, f.getvalue(), f.type)},
                timeout=120,
            )
            (success if r.status_code == 200 else failed).append(f.name)
        except Exception as e:
            failed.append(f"{f.name} ({e})")
        bar.progress((i + 1) / len(files), text=f"Indexed {i+1}/{len(files)}")
    bar.empty()

    if success:
        st.markdown(f"""
        <div style="
            background:rgba(0,212,170,0.06); border:1px solid rgba(0,212,170,0.2);
            border-radius:10px; padding:0.55rem 1rem; margin-top:0.4rem;
            font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:#00d4aa;
        ">✓ Indexed: {', '.join(success)}</div>
        """, unsafe_allow_html=True)
    if failed:
        st.markdown(f"""
        <div style="
            background:rgba(255,100,100,0.06); border:1px solid rgba(255,100,100,0.2);
            border-radius:10px; padding:0.55rem 1rem; margin-top:0.4rem;
            font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:#ff6464;
        ">✗ Failed: {', '.join(failed)}</div>
        """, unsafe_allow_html=True)


def _explain_files(files, api_url: str):
    for f in files:
        with st.spinner(f"Summarizing '{f.name}'…"):
            try:
                r = requests.post(
                    f"{api_url}/summarize",
                    files={"file": (f.name, f.getvalue(), f.type)},
                    timeout=180,
                )
            except Exception as e:
                st.error(f"Backend unreachable: {e}")
                continue

        if r.status_code != 200:
            st.error(f"Summarization failed: {r.text}")
            continue

        summary = r.json().get("summary", "No summary returned.")
        parts   = re.split(r"(```[\w]*\n[\s\S]*?```)", summary)

        st.markdown(f"""
        <div style="
            background:rgba(120,100,255,0.05);
            border:1px solid rgba(120,100,255,0.15);
            border-left:2px solid #7864ff;
            border-radius:4px 14px 14px 14px;
            padding:1rem 1.2rem; margin:0.8rem 0;
        ">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.65rem;">
                <span style="font-size:1rem;">📄</span>
                <span style="font-family:'Outfit',sans-serif; font-weight:700;
                             font-size:0.88rem; color:rgba(240,238,255,0.9);">{f.name}</span>
                <span style="
                    font-family:'JetBrains Mono',monospace; font-size:0.62rem;
                    color:#7864ff; background:rgba(120,100,255,0.1);
                    border:1px solid rgba(120,100,255,0.2);
                    border-radius:99px; padding:0.15rem 0.5rem;
                ">Document Summary</span>
            </div>
        """, unsafe_allow_html=True)

        for part in parts:
            if part.startswith("```"):
                lines = part.strip().split("\n")
                lang  = lines[0].replace("```", "").strip() or "text"
                code  = "\n".join(lines[1:]).rstrip("`").strip()
                st.code(code, language=lang)
            elif part.strip():
                formatted = part.replace("\n", "<br>")
                st.markdown(
                    f"<div style='font-family:Outfit,sans-serif; font-size:0.88rem;"
                    f"color:rgba(240,238,255,0.75); line-height:1.7;'>{formatted}</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)