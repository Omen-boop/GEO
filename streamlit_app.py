import streamlit as st
import pdfplumber
import anthropic
import json
import re
import tempfile
import os

st.set_page_config(
    page_title="FactCheck Agent",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #0f0f0f; color: #f0f0f0; }
    .stApp { background-color: #0f0f0f; }
    h1 { color: #00e5ff; font-family: 'Courier New', monospace; }
    h3 { color: #00e5ff; }
    .verified { background-color: #0d3b1e; border-left: 4px solid #00c853; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .inaccurate { background-color: #3b1a0d; border-left: 4px solid #ff6d00; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .false { background-color: #3b0d0d; border-left: 4px solid #d50000; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .unverified { background-color: #1a1a2e; border-left: 4px solid #9e9e9e; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .claim-box { background-color: #1a1a1a; padding: 16px; border-radius: 8px; margin: 10px 0; }
    .stButton>button { background-color: #00e5ff; color: #000; font-weight: bold; border-radius: 6px; border: none; padding: 10px 24px; }
    .stButton>button:hover { background-color: #00b8d4; }
    .metric-card { background: #1a1a1a; padding: 16px; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🔍 FactCheck Agent")
st.markdown("*Automated claim verification from PDF documents using live web data*")
st.markdown("---")

def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_claims(text):
    client = anthropic.Anthropic()
    prompt = f"""You are a fact-extraction expert. Extract all verifiable factual claims from this document.
Focus on: statistics, percentages, dates, numbers, named entities, financial figures, technical claims, scientific claims.

Return ONLY a JSON array of claims, no preamble or markdown:
[
  {{"claim": "exact claim text", "category": "statistic|date|financial|technical|general", "context": "brief context"}}
]

Extract 5-15 most verifiable claims. Document:
{text[:8000]}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    claims = json.loads(raw)
    return claims

def verify_claim(claim_obj):
    client = anthropic.Anthropic()
    
    prompt = f"""You are a rigorous fact-checker. Verify this claim using your knowledge and web search.

Claim: "{claim_obj['claim']}"
Category: {claim_obj['category']}
Context: {claim_obj['context']}

Search the web for current, accurate information to verify this claim.
Then respond with ONLY a JSON object (no markdown, no preamble):
{{
  "verdict": "VERIFIED|INACCURATE|FALSE|UNVERIFIED",
  "confidence": 0-100,
  "explanation": "2-3 sentence explanation of your finding",
  "correct_value": "the actual correct value/fact if claim is wrong, else null",
  "sources": ["source description 1", "source description 2"]
}}

Verdict guide:
- VERIFIED: Claim is accurate and confirmed by evidence
- INACCURATE: Claim exists but numbers/dates/details are wrong (outdated or imprecise)
- FALSE: Claim is factually incorrect or fabricated
- UNVERIFIED: Cannot confirm or deny with available evidence"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Get the final text response
    result_text = ""
    for block in response.content:
        if block.type == "text":
            result_text = block.text.strip()
    
    if not result_text:
        return {
            "verdict": "UNVERIFIED",
            "confidence": 0,
            "explanation": "Could not retrieve verification results.",
            "correct_value": None,
            "sources": []
        }
    
    clean = re.sub(r"```json|```", "", result_text).strip()
    # Extract JSON if there's extra text
    json_match = re.search(r'\{.*\}', clean, re.DOTALL)
    if json_match:
        clean = json_match.group()
    
    result = json.loads(clean)
    return result

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

# --- UI ---
col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader(
        "Upload your PDF document",
        type=["pdf"],
        help="Upload any PDF with factual claims — marketing reports, research, news articles, etc."
    )

with col2:
    st.markdown("""
    **How it works:**
    1. 📄 Upload a PDF
    2. 🧠 AI extracts key claims
    3. 🌐 Live web search verifies each
    4. 📊 Get a full truth report
    """)

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    if st.button("🚀 Run Fact-Check"):
        results = []
        
        # Step 1: Extract text
        with st.spinner("📄 Extracting text from PDF..."):
            try:
                pdf_text = extract_text_from_pdf(tmp_path)
                st.success(f"✅ Extracted {len(pdf_text.split())} words from PDF")
            except Exception as e:
                st.error(f"Failed to read PDF: {e}")
                st.stop()
        
        # Step 2: Extract claims
        with st.spinner("🧠 Identifying verifiable claims..."):
            try:
                claims = extract_claims(pdf_text)
                st.success(f"✅ Found {len(claims)} verifiable claims")
            except Exception as e:
                st.error(f"Failed to extract claims: {e}")
                st.stop()
        
        st.markdown("---")
        st.markdown(f"### 📋 Verifying {len(claims)} Claims...")
        
        progress = st.progress(0)
        status_text = st.empty()
        
        # Step 3: Verify each claim
        for i, claim_obj in enumerate(claims):
            status_text.text(f"Checking claim {i+1}/{len(claims)}: {claim_obj['claim'][:60]}...")
            try:
                verification = verify_claim(claim_obj)
                results.append({**claim_obj, **verification})
            except Exception as e:
                results.append({
                    **claim_obj,
                    "verdict": "UNVERIFIED",
                    "confidence": 0,
                    "explanation": f"Verification error: {str(e)}",
                    "correct_value": None,
                    "sources": []
                })
            progress.progress((i + 1) / len(claims))
        
        status_text.empty()
        progress.empty()
        
        # --- Results ---
        st.markdown("---")
        st.markdown("## 📊 Fact-Check Report")
        
        # Summary metrics
        verified = sum(1 for r in results if r["verdict"] == "VERIFIED")
        inaccurate = sum(1 for r in results if r["verdict"] == "INACCURATE")
        false_c = sum(1 for r in results if r["verdict"] == "FALSE")
        unverified = sum(1 for r in results if r["verdict"] == "UNVERIFIED")
        
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("✅ Verified", verified)
        with m2:
            st.metric("⚠️ Inaccurate", inaccurate)
        with m3:
            st.metric("❌ False", false_c)
        with m4:
            st.metric("❓ Unverified", unverified)
        
        st.markdown("---")
        
        # Detailed results
        for i, r in enumerate(results):
            css_class = verdict_color(r["verdict"])
            emoji = verdict_emoji(r["verdict"])
            
            with st.expander(f"{emoji} [{r['verdict']}] {r['claim'][:80]}...", expanded=(r["verdict"] in ["FALSE", "INACCURATE"])):
                st.markdown(f"<div class='{css_class}'>", unsafe_allow_html=True)
                
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.markdown(f"**Claim:** {r['claim']}")
                    st.markdown(f"**Finding:** {r['explanation']}")
                    if r.get("correct_value"):
                        st.markdown(f"**Correct Value:** `{r['correct_value']}`")
                    if r.get("sources"):
                        st.markdown(f"**Sources:** {' • '.join(r['sources'][:2])}")
                with col_b:
                    st.markdown(f"**Category:** `{r['category']}`")
                    st.markdown(f"**Confidence:** `{r.get('confidence', 'N/A')}%`")
                
                st.markdown("</div>", unsafe_allow_html=True)
        
        # Download report
        report_json = json.dumps(results, indent=2)
        st.download_button(
            "📥 Download Full Report (JSON)",
            data=report_json,
            file_name="factcheck_report.json",
            mime="application/json"
        )
        
        os.unlink(tmp_path)

else:
    st.info("👆 Upload a PDF to begin. Works best with reports, articles, or marketing content containing factual claims.")
    
    st.markdown("### 🎯 What gets checked?")
    cols = st.columns(3)
    with cols[0]:
        st.markdown("**📈 Statistics**\nPercentages, growth rates, market sizes")
    with cols[1]:
        st.markdown("**📅 Dates & Events**\nTimelines, launches, historical facts")
    with cols[2]:
        st.markdown("**💰 Financial Data**\nRevenue, valuations, funding amounts")
