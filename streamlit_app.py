import streamlit as st
import pdfplumber
import json
import re
import tempfile
import os
import google.generativeai as genai

# ---------------- GEMINI API ----------------

GEMINI_API_KEY = "AIzaSyAhdv5yqjxUimjZzK3K8AntW3fqWBm5PBM"

genai.configure(api_key=GEMINI_API_KEY)

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide"
)

# ---------------- CSS ----------------

st.markdown("""
<style>
.stApp {
    background-color: #0f0f0f;
    color: white;
}

h1,h2,h3 {
    color: #00e5ff;
}

.stButton>button {
    background-color: #00e5ff;
    color: black;
    border-radius: 8px;
    border: none;
    font-weight: bold;
}

.result-box {
    padding: 15px;
    border-radius: 10px;
    margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------

st.title("🔍 FactCheck Agent")

st.markdown("AI-powered PDF fact checking system")

st.markdown("---")

# ---------------- PDF TEXT EXTRACTION ----------------

def extract_text_from_pdf(pdf_file):

    text = ""

    with pdfplumber.open(pdf_file) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

    return text

# ---------------- CLAIM EXTRACTION ----------------

def extract_claims(text):

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
Extract factual claims from the following text.

Focus on:
- statistics
- dates
- percentages
- money values
- scientific claims

Return ONLY valid JSON array.

Format:
[
 {{
   "claim": "claim text",
   "category": "type"
 }}
]

TEXT:
{text[:6000]}
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = re.sub(r"```json|```", "", raw).strip()

    json_match = re.search(r'\[.*\]', raw, re.DOTALL)

    if json_match:
        raw = json_match.group()

    claims = json.loads(raw)

    return claims

# ---------------- CLAIM VERIFICATION ----------------

def verify_claim(claim_obj):

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
Verify this factual claim.

Claim:
{claim_obj['claim']}

Return ONLY valid JSON:

{{
 "verdict":"VERIFIED or FALSE or INACCURATE",
 "confidence":"0-100",
 "explanation":"short explanation"
}}
"""

    response = model.generate_content(prompt)

    raw = response.text.strip()

    raw = re.sub(r"```json|```", "", raw).strip()

    json_match = re.search(r'\{.*\}', raw, re.DOTALL)

    if json_match:
        raw = json_match.group()

    result = json.loads(raw)

    return result

# ---------------- FILE UPLOAD ----------------

uploaded_file = st.file_uploader(
    "Upload PDF File",
    type=["pdf"]
)

# ---------------- MAIN FLOW ----------------

if uploaded_file:

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:

        tmp.write(uploaded_file.read())

        tmp_path = tmp.name

    if st.button("🚀 Start Fact Check"):

        # Extract text

        with st.spinner("📄 Reading PDF..."):

            try:

                pdf_text = extract_text_from_pdf(tmp_path)

                st.success("PDF text extracted successfully")

            except Exception as e:

                st.error(f"PDF extraction failed: {e}")

                st.stop()

        # Extract claims

        with st.spinner("🧠 Extracting claims..."):

            try:

                claims = extract_claims(pdf_text)

                st.success(f"{len(claims)} claims found")

            except Exception as e:

                st.error(f"Claim extraction failed: {e}")

                st.stop()

        st.markdown("---")

        st.header("📊 Verification Results")

        # Verify claims

        for claim_obj in claims:

            with st.spinner(f"Checking: {claim_obj['claim'][:50]}..."):

                try:

                    result = verify_claim(claim_obj)

                    verdict = result.get("verdict", "UNKNOWN")

                    if verdict == "VERIFIED":
                        color = "#0d3b1e"

                    elif verdict == "FALSE":
                        color = "#3b0d0d"

                    else:
                        color = "#3b1a0d"

                    st.markdown(
                        f"""
<div class="result-box" style="background:{color}">
<h4>{verdict}</h4>
<p><b>Claim:</b> {claim_obj['claim']}</p>
<p><b>Explanation:</b> {result.get('explanation')}</p>
<p><b>Confidence:</b> {result.get('confidence')}</p>
</div>
""",
                        unsafe_allow_html=True
                    )

                except Exception as e:

                    st.error(f"Verification failed: {e}")

else:

    st.info("Upload a PDF file to begin fact checking.")
