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

# ---------------- CUSTOM CSS ----------------

st.markdown("""
<style>
    .stApp {
        background-color: #0f0f0f;
        color: #f0f0f0;
    }

    h1, h2, h3 {
        color: #00e5ff;
    }

    .verified {
        background-color: #0d3b1e;
        border-left: 5px solid #00c853;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }

    .inaccurate {
        background-color: #3b1a0d;
        border-left: 5px solid #ff9100;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }

    .false {
        background-color: #3b0d0d;
        border-left: 5px solid #ff1744;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }

    .unverified {
        background-color: #1f1f1f;
        border-left: 5px solid #9e9e9e;
        padding: 12px;
        border-radius: 6px;
        margin: 10px 0;
    }

    .stButton > button {
        background-color: #00e5ff;
        color: black;
        border-radius: 8px;
        border: none;
        padding: 10px 25px;
        font-weight: bold;
    }

    .stButton > button:hover {
        background-color: #00bcd4;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------

st.title("🔍 FactCheck Agent")
st.markdown("### AI Powered PDF Claim Verification System")
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

    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
Extract important factual claims from the following text.

Focus on:
- statistics
- percentages
- dates
- money values
- scientific claims
- technical claims

Return ONLY valid JSON array.

Format:
[
 {{
   "claim": "claim text",
   "category": "statistic",
   "context": "short context"
 }}
]

TEXT:
{text[:7000]}
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

    model = genai.GenerativeModel("gemini-pro")

    prompt = f"""
You are a professional fact checker.

Verify this claim:

Claim: "{claim_obj['claim']}"

Respond ONLY in JSON format:

{{
  "verdict": "VERIFIED or INACCURATE or FALSE or UNVERIFIED",
  "confidence": 90,
  "explanation": "short explanation",
  "correct_value": "correct value if wrong",
  "sources": ["source1", "source2"]
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

# ---------------- HELPERS ----------------

def verdict_color(verdict):

    return {
        "VERIFIED": "verified",
        "INACCURATE": "inaccurate",
        "FALSE": "false",
        "UNVERIFIED": "unverified"
    }.get(verdict, "unverified")

def verdict_emoji(verdict):

    return {
        "VERIFIED": "✅",
        "INACCURATE": "⚠️",
        "FALSE": "❌",
        "UNVERIFIED": "❓"
    }.get(verdict, "❓")

# ---------------- UI ----------------

uploaded_file = st.file_uploader(
    "Upload PDF File",
    type=["pdf"]
)

if uploaded_file:

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:

        tmp.write(uploaded_file.read())

        tmp_path = tmp.name

    if st.button("🚀 Start Fact Check"):

        # STEP 1

        with st.spinner("📄 Reading PDF..."):

            try:

                pdf_text = extract_text_from_pdf(tmp_path)

                st.success("PDF text extracted successfully")

            except Exception as e:

                st.error(f"PDF Error: {e}")

                st.stop()

        # STEP 2

        with st.spinner("🧠 Extracting claims..."):

            try:

                claims = extract_claims(pdf_text)

                st.success(f"{len(claims)} claims found")

            except Exception as e:

                st.error(f"Claim extraction failed: {e}")

                st.stop()

        # STEP 3

        results = []

        progress = st.progress(0)

        for i, claim_obj in enumerate(claims):

            try:

                verification = verify_claim(claim_obj)

                results.append({
                    **claim_obj,
                    **verification
                })

            except Exception as e:

                results.append({
                    **claim_obj,
                    "verdict": "UNVERIFIED",
                    "confidence": 0,
                    "explanation": str(e),
                    "correct_value": None,
                    "sources": []
                })

            progress.progress((i + 1) / len(claims))

        # ---------------- RESULTS ----------------

        st.markdown("---")
        st.header("📊 Fact Check Results")

        verified = sum(1 for r in results if r["verdict"] == "VERIFIED")
        inaccurate = sum(1 for r in results if r["verdict"] == "INACCURATE")
        false_count = sum(1 for r in results if r["verdict"] == "FALSE")
        unverified = sum(1 for r in results if r["verdict"] == "UNVERIFIED")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("✅ Verified", verified)
        c2.metric("⚠️ Inaccurate", inaccurate)
        c3.metric("❌ False", false_count)
        c4.metric("❓ Unverified", unverified)

        st.markdown("---")

        for r in results:

            css_class = verdict_color(r["verdict"])

            emoji = verdict_emoji(r["verdict"])

            with st.expander(f"{emoji} {r['claim'][:80]}"):

                st.markdown(
                    f"<div class='{css_class}'>",
                    unsafe_allow_html=True
                )

                st.markdown(f"### Verdict: {r['verdict']}")

                st.write("**Claim:**")
                st.write(r["claim"])

                st.write("**Explanation:**")
                st.write(r["explanation"])

                if r.get("correct_value"):
                    st.write("**Correct Value:**")
                    st.write(r["correct_value"])

                if r.get("sources"):
                    st.write("**Sources:**")
                    st.write(", ".join(r["sources"]))

                st.markdown("</div>", unsafe_allow_html=True)

        # ---------------- DOWNLOAD REPORT ----------------

        report_json = json.dumps(results, indent=2)

        st.download_button(
            "📥 Download JSON Report",
            data=report_json,
            file_name="factcheck_report.json",
            mime="application/json"
        )

        os.unlink(tmp_path)

else:

    st.info("👆 Upload a PDF document to begin fact checking.")

    st.markdown("""
### Features
- 📄 PDF Upload
- 🧠 AI Claim Extraction
- 🌐 Fact Verification
- 📊 Truth Report
- 📥 JSON Download
""")
