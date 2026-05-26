import streamlit as st
import PyPDF2
from openai import OpenAI
from duckduckgo_search import DDGS

st.set_page_config(page_title="AI Fact-Checker", page_icon="🔍")
st.title("Truth Layer: Automated PDF Fact-Checker")

api_key = st.sidebar.text_input("open AI key here ", type="password")

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_claims(text, client):
    prompt = f"Extract the top 3-5 specific verifiable claims (stats, dates, financial figures) from this text. Return them as a simple numbered list:\n\n{text[:3000]}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.split('\n')

def verify_claim(claim, client):
    # Search the web
    with DDGS() as ddgs:
        results = [r for r in ddgs.text(claim, max_results=3)]
    
    search_context = "\n".join([f"- {r['body']}" for r in results])
    
    # Evaluate
    prompt = f"""
    Claim: {claim}
    Live Web Data: {search_context}
    
    Based on the live data, categorize the claim as:
    VERIFIED (matches data), INACCURATE (outdated stats), or FALSE (no evidence).
    Provide a 1-sentence explanation with the real facts.
    Format: [STATUS] - [Explanation]
    """
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

uploaded_file = st.file_uploader("Upload a document (PDF)", type="pdf")

if uploaded_file and api_key:
    if st.button("Run Fact-Check"):
        client = OpenAI(api_key=api_key)
        
        with st.spinner("Extracting text from PDF..."):
            text = extract_text_from_pdf(uploaded_file)
            
        with st.spinner("Identifying claims..."):
            claims = extract_claims(text, client)
            claims = [c for c in claims if c.strip() != ""]
            
        st.subheader("Results")
        for claim in claims:
            st.markdown(f"**Claim Extracted:** {claim}")
            with st.spinner("Verifying via live web search..."):
                try:
                    result = verify_claim(claim, client)
                    if "VERIFIED" in result.upper():
                        st.success(result)
                    elif "FALSE" in result.upper():
                        st.error(result)
                    else:
                        st.warning(result)
                except Exception as e:
                    st.error("Search rate limit hit or error analyzing claim.")
            st.divider()
elif not api_key:
    st.info("Please enter your OpenAI API key in the sidebar to begin.")
