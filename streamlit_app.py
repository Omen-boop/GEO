import streamlit as st
import pdfplumber
import google.generativeai as genai
import json
import re
import tempfile

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide"
)

# ---------------- GEMINI API ----------------

GEMINI_API_KEY = "AIzaSyAhdv5yqjxUimjZzK3K8AntW3fqWBm5PBM"

genai.configure(api_key=GEMINI_API_KEY)

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Segoe UI', sans-serif;
}

.stApp {
    background: linear-gradient(135deg, #0f172a, #111827);
    color: white;
}

.main-title {
    font-size: 48px;
    font-weight: bold;
    color: #38bdf8;
    text-align: center;
    margin-top: 10px;
}

.sub-title {
    text-align: center;
    color: #cbd5e1;
    font-size: 18px;
    margin-bottom: 30px;
}

.upload-box {
    background: rgba(255,255,255,0.05);
    padding: 25px;
    border-radius: 18px;
    border: 1px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
}

.stButton > button {
    background: linear-gradient(90deg, #06b6d4, #3b82f6);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 14px 28px;
    font-size: 18px;
    font-weight: bold;
    width: 100%;
    transition: 0.3s;
}

.stButton > button:hover {
    transform: scale(1.02);
    background: linear-gradient(90deg, #0891b2, #2563eb);
}

.metric-card {
    background: rgba(255,255,255,0.06);
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
}

.result-card {
    padding: 20px;
    border-radius: 18px;
    margin-top: 15px;
    border-left: 6px solid;
    box-shadow: 0 0 15px rgba(0,0,0,0.3);
}

.verified {
    background: rgba(0,255,120,0.08);
    border-color: #00e676;
}

.false {
    background: rgba(255,0,80,0.08);
    border-color: #ff1744;
}

.inaccurate {
    background: rgba(255,170,0,0.08);
    border-color: #ff9100;
}

.footer {
    text-align: center;
    margin-top: 40px;
    color: #94a3b8;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.markdown(
    """
<div class="main-title">
🔍 FactCheck Agent
</div>

<div class="sub-title">
AI Powered PDF Fact Verification System
</div>
""",
    unsafe_allow_html=True
)

# ---------------- FUNCTIONS ----------------

def extract_text_from_pdf(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text

# ---------------- CLAIM EXTRACTION ----------------

def extract_claims(text):

    model = genai.GenerativeModel(
        model_name="models/gemini-1.5-flash"
    )

    prompt = f"""
Extract factual claims from this text.

Focus on:
- dates
- statistics
- percentages
- financial figures
- scientific claims

Return ONLY valid JSON array.

Example:
[
 {{
   "claim":"Tesla was founded in 2003",
   "category":"date"
 }}
]

TEXT:
{text[:5000]}
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = re.sub(r"```json|```", "", raw).strip()

    match = re.search(r'\[.*\]', raw, re.DOTALL)

    if match:
        raw = match.group()

    claims = json.loads(raw)

    return claims

# ---------------- VERIFY CLAIM ----------------

def verify_claim(claim):

    model = genai.GenerativeModel(
        model_name="models/gemini-1.5-flash"
    )

    prompt = f"""
Verify this factual claim.

Claim:
{claim}

Return ONLY valid JSON.

Format:
{{
 "verdict":"VERIFIED or FALSE or INACCURATE",
 "confidence":"0-100",
 "explanation":"short explanation"
}}
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = re.sub(r"```json|```", "", raw).strip()

    match = re.search(r'\{.*\}', raw, re.DOTALL)

    if match:
        raw = match.group()

    result = json.loads(raw)

    return result

# ---------------- UPLOAD SECTION ----------------

st.markdown('<div class="upload-box">', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "📄 Upload PDF File",
    type=["pdf"]
)

st.markdown('</div>', unsafe_allow_html=True)

# ---------------- MAIN ----------------

if uploaded_file:

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:

        tmp.write(uploaded_file.read())

        tmp_path = tmp.name

    if st.button("🚀 Start Fact Check"):

        # PDF Extraction

        with st.spinner("📄 Extracting PDF text..."):

            try:

                pdf_text = extract_text_from_pdf(tmp_path)

                st.success("PDF text extracted successfully")

            except Exception as e:

                st.error(f"PDF extraction failed: {e}")

                st.stop()

        # Claim Extraction

        with st.spinner("🧠 Extracting claims..."):

            try:

                claims = extract_claims(pdf_text)

                st.success(f"{len(claims)} claims extracted")

            except Exception as e:

                st.error(f"Claim extraction failed: {e}")

                st.stop()

        st.markdown("---")

        verified_count = 0
        false_count = 0
        inaccurate_count = 0

        results = []

        # Verification

        for claim_obj in claims:

            claim_text = claim_obj["claim"]

            with st.spinner(f"Checking: {claim_text[:50]}..."):

                try:

                    result = verify_claim(claim_text)

                    verdict = result.get("verdict", "UNKNOWN")

                    if verdict == "VERIFIED":
                        verified_count += 1

                    elif verdict == "FALSE":
                        false_count += 1

                    else:
                        inaccurate_count += 1

                    results.append({
                        "claim": claim_text,
                        "result": result
                    })

                except Exception as e:

                    st.error(f"Verification failed: {e}")

        # ---------------- METRICS ----------------

        st.markdown("## 📊 Report Summary")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.markdown(
                f"""
<div class="metric-card">
<h2>✅ {verified_count}</h2>
<p>Verified</p>
</div>
""",
                unsafe_allow_html=True
            )

        with c2:
            st.markdown(
                f"""
<div class="metric-card">
<h2>❌ {false_count}</h2>
<p>False</p>
</div>
""",
                unsafe_allow_html=True
            )

        with c3:
            st.markdown(
                f"""
<div class="metric-card">
<h2>⚠️ {inaccurate_count}</h2>
<p>Inaccurate</p>
</div>
""",
                unsafe_allow_html=True
            )

        st.markdown("---")

        # ---------------- RESULTS ----------------

        st.markdown("## 🔎 Detailed Results")

        for item in results:

            claim = item["claim"]

            result = item["result"]

            verdict = result.get("verdict", "UNKNOWN")

            explanation = result.get("explanation", "")

            confidence = result.get("confidence", "")

            if verdict == "VERIFIED":
                card_class = "verified"

            elif verdict == "FALSE":
                card_class = "false"

            else:
                card_class = "inaccurate"

            st.markdown(
                f"""
<div class="result-card {card_class}">
<h3>{verdict}</h3>

<p><b>Claim:</b><br>{claim}</p>

<p><b>Explanation:</b><br>{explanation}</p>

<p><b>Confidence:</b> {confidence}</p>
</div>
""",
                unsafe_allow_html=True
            )

# ---------------- FOOTER ----------------

st.markdown(
    """
<div class="footer">
Built with Gemini AI • Streamlit • PDF Fact Verification
</div>
""",
    unsafe_allow_html=True
)
