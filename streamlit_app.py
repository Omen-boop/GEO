import streamlit as st
import pdfplumber
import google.generativeai as genai
import tempfile
import json
import re

# ---------------- API ----------------

genai.configure(api_key="AIzaSyAhdv5yqjxUimjZzK3K8AntW3fqWBm5PBM")

# ---------------- PAGE ----------------

st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide"
)

# ---------------- CSS ----------------

st.markdown("""
<style>

.stApp {
    background-color: #0f172a;
    color: white;
}

.title {
    text-align:center;
    font-size:48px;
    font-weight:bold;
    color:#38bdf8;
}

.subtitle {
    text-align:center;
    color:#cbd5e1;
    margin-bottom:30px;
}

.stButton>button {
    width:100%;
    background:#06b6d4;
    color:white;
    border:none;
    border-radius:10px;
    padding:14px;
    font-size:18px;
    font-weight:bold;
}

.result {
    padding:20px;
    border-radius:12px;
    margin-top:15px;
}

.green {
    background:#052e16;
}

.red {
    background:#450a0a;
}

.orange {
    background:#431407;
}

</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.markdown('<div class="title">🔍 FactCheck Agent</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="subtitle">AI Powered PDF Fact Verification</div>',
    unsafe_allow_html=True
)

# ---------------- PDF TEXT ----------------

def extract_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text

    return text

# ---------------- CLAIMS ----------------

def extract_claims(text):

    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
Extract factual claims from this text.

Return ONLY valid JSON array.

Example:
[
 {{
   "claim":"India population is 1.4 billion"
 }}
]

TEXT:
{text[:4000]}
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = re.sub(r"```json|```", "", raw)

    match = re.search(r'\[.*\]', raw, re.DOTALL)

    if match:
        raw = match.group()

    claims = json.loads(raw)

    return claims

# ---------------- VERIFY ----------------

def verify_claim(claim):

    model = genai.GenerativeModel("models/gemini-1.5-flash")

    prompt = f"""
Verify this claim:

{claim}

Return ONLY valid JSON:

{{
 "verdict":"VERIFIED or FALSE or INACCURATE",
 "explanation":"short explanation",
 "confidence":"0-100"
}}
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = re.sub(r"```json|```", "", raw)

    match = re.search(r'\{.*\}', raw, re.DOTALL)

    if match:
        raw = match.group()

    result = json.loads(raw)

    return result

# ---------------- UI ----------------

uploaded_file = st.file_uploader(
    "📄 Upload PDF File",
    type=["pdf"]
)

if uploaded_file:

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:

        tmp.write(uploaded_file.read())

        tmp_path = tmp.name

    if st.button("🚀 Start Fact Check"):

        with st.spinner("📄 Extracting PDF text..."):

            text = extract_text(tmp_path)

        st.success("PDF extracted successfully")

        with st.spinner("🧠 Extracting claims..."):

            claims = extract_claims(text)

        st.success(f"{len(claims)} claims found")

        st.markdown("---")

        for item in claims:

            claim = item["claim"]

            with st.spinner(f"Checking: {claim[:40]}"):

                result = verify_claim(claim)

            verdict = result["verdict"]

            if verdict == "VERIFIED":
                box = "green"

            elif verdict == "FALSE":
                box = "red"

            else:
                box = "orange"

            st.markdown(
                f'''
<div class="result {box}">
<h3>{verdict}</h3>
<p><b>Claim:</b> {claim}</p>
<p><b>Explanation:</b> {result["explanation"]}</p>
<p><b>Confidence:</b> {result["confidence"]}</p>
</div>
''',
                unsafe_allow_html=True
            )

else:

    st.info("Upload a PDF file to begin.")
