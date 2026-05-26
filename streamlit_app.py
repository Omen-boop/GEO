import streamlit as st
import pdfplumber
import google.generativeai as genai
import json

genai.configure(api_key="AIzaSyBm5ekx-Mrft2H-5ZxpMC5BOyqb2wAZzCQ")
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="FactCheck Agent", page_icon="🔍", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');
    html, body, [class*="css"] { font-family: 'Syne', sans-serif; background: #0a0a0f; color: #e8e6f0; }
    .stApp { background: #0a0a0f; }
    .verdict-card { border-radius: 12px; padding: 1.2rem 1.5rem; margin: 0.75rem 0; border-left: 4px solid; font-size: 0.88rem; line-height: 1.6; }
    .verdict-true { background: #052e16; border-color: #16a34a; color: #bbf7d0; }
    .verdict-false { background: #2d0a0a; border-color: #dc2626; color: #fecaca; }
    .verdict-unverified { background: #1c1410; border-color: #d97706; color: #fde68a; }
    .claim-text { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.4rem; color: #f1f5f9; }
    .verdict-badge { display: inline-block; padding: 2px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; margin-bottom: 0.5rem; }
    .badge-true { background: #16a34a; color: #fff; }
    .badge-false { background: #dc2626; color: #fff; }
    .badge-unverified { background: #d97706; color: #fff; }
    .summary-box { background: #12121a; border: 1px solid #1e1e2e; border-radius: 16px; padding: 1.5rem 2rem; margin: 1.5rem 0; display: flex; gap: 2rem; justify-content: center; flex-wrap: wrap; }
    .stat { text-align: center; }
    .stat-num { font-size: 2.5rem; font-weight: 800; }
    .stat-label { font-size: 0.8rem; color: #6b7280; }
    .green { color: #4ade80; } .red { color: #f87171; } .yellow { color: #fbbf24; }
    .stButton button { background: linear-gradient(135deg, #7c3aed, #4f46e5); color: white; border: none; border-radius: 10px; padding: 0.6rem 2rem; font-weight: 700; font-size: 1rem; width: 100%; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style='text-align:center;padding:3rem 0 2rem'>
      <h1 style='font-size:3rem;font-weight:800;background:linear-gradient(135deg,#c084fc,#818cf8,#38bdf8);-webkit-background-clip:text;-webkit-text-fill-color:transparent'>
        🔍 FactCheck Agent
      </h1>
      <p style='color:#6b7280;font-size:1.1rem'>Automated claim verification from PDF documents using AI</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def extract_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text[:12000]


def extract_claims(text):
    prompt = (
        "Extract 5-10 specific verifiable claims from this text.\n"
        "Focus on: statistics, dates, named facts, percentages, numerical data.\n"
        "Return ONLY a JSON array of strings, no explanation, no markdown.\n\n"
        "Text:\n" + text + "\n\nReturn format: [\"claim 1\", \"claim 2\", ...]"
    )
    resp = model.generate_content(prompt)
    raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        lines = [l.strip().lstrip("-*").strip() for l in raw.splitlines() if l.strip()]
        return [l for l in lines if len(l) > 15][:10]


def verify_claim(claim):
    prompt = (
        "You are a strict fact-checker. Verify this claim using your knowledge.\n\n"
        "Claim: " + claim + "\n\n"
        "Respond ONLY with a JSON object, no markdown:\n"
        '{"verdict": "TRUE" or "FALSE" or "UNVERIFIED", '
        '"explanation": "1-2 sentence explanation", '
        '"corrected_fact": "corrected version if FALSE, else null"}'
    )
    resp = model.generate_content(prompt)
    raw = resp.text.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"verdict": "UNVERIFIED", "explanation": resp.text[:200], "corrected_fact": None}


uploaded = st.file_uploader("Upload your PDF document", type=["pdf"])

if uploaded:
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        run = st.button("🚀 Run FactCheck")

    if run:
        with st.spinner("📄 Extracting text from PDF..."):
            text = extract_text(uploaded)
        if not text.strip():
            st.error("Could not extract text. Please upload a text-based PDF.")
            st.stop()

        with st.spinner("🧠 Identifying claims with AI..."):
            claims = extract_claims(text)

        if not claims:
            st.warning("No verifiable claims found.")
            st.stop()

        st.markdown(f"**Found {len(claims)} claims — verifying each...**")
        st.markdown("---")

        results = []
        progress = st.progress(0)
        for i, claim in enumerate(claims):
            with st.spinner(f"🔎 Verifying claim {i+1}/{len(claims)}..."):
                result = verify_claim(claim)
                result["claim"] = claim
                results.append(result)
            progress.progress((i + 1) / len(claims))
        progress.empty()

        true_count = sum(1 for r in results if r["verdict"] == "TRUE")
        false_count = sum(1 for r in results if r["verdict"] == "FALSE")
        unver_count = sum(1 for r in results if r["verdict"] == "UNVERIFIED")

        st.markdown(
            f"""
            <div class="summary-box">
              <div class="stat"><div class="stat-num green">{true_count}</div><div class="stat-label">VERIFIED TRUE</div></div>
              <div class="stat"><div class="stat-num red">{false_count}</div><div class="stat-label">FALSE / MISLEADING</div></div>
              <div class="stat"><div class="stat-num yellow">{unver_count}</div><div class="stat-label">UNVERIFIED</div></div>
              <div class="stat"><div class="stat-num">{len(results)}</div><div class="stat-label">TOTAL CLAIMS</div></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("## 📋 Detailed Results")
        for r in results:
            v = r["verdict"]
            css = {"TRUE": "verdict-true", "FALSE": "verdict-false"}.get(v, "verdict-unverified")
            badge = {"TRUE": "badge-true", "FALSE": "badge-false"}.get(v, "badge-unverified")
            icon = {"TRUE": "✅", "FALSE": "❌"}.get(v, "⚠️")
            correction = ""
            if r.get("corrected_fact"):
                correction = (
                    '<div style="margin-top:0.5rem;padding:0.5rem;'
                    'background:rgba(220,38,38,0.1);border-radius:6px;">'
                    "<b>✏️ Correction:</b> " + r["corrected_fact"] + "</div>"
                )
            st.markdown(
                f"""
                <div class="verdict-card {css}">
                  <div class="claim-text">"{r['claim']}"</div>
                  <span class="verdict-badge {badge}">{icon} {v}</span>
                  <div>{r['explanation']}</div>
                  {correction}
                </div>
                """,
                unsafe_allow_html=True,
            )

else:
    c1, c2, c3, c4 = st.columns(4)
    for col, icon, title, desc in [
        (c1, "📄", "Upload PDF", "Any text-based PDF"),
        (c2, "🧠", "AI Extracts Claims", "Gemini finds key facts"),
        (c3, "🌐", "AI Verifies", "Each claim cross-checked"),
        (c4, "📊", "Truth Report", "TRUE / FALSE / UNVERIFIED"),
    ]:
        with col:
            st.markdown(
                f'<div style="text-align:center;padding:1.5rem;background:#12121a;border-radius:12px;border:1px solid #1e1e2e;">'
                f'<div style="font-size:2rem">{icon}</div>'
                f'<div style="font-weight:700;margin:0.5rem 0">{title}</div>'
                f'<div style="font-size:0.8rem;color:#6b7280">{desc}</div></div>',
                unsafe_allow_html=True,
            )
