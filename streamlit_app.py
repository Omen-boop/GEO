import streamlit as st
from PyPDF2 import PdfReader
import re
import google.generativeai as genai

# Gemini API Key
genai.configure(api_key="YOUR_GEMINI_API_KEY")

model = genai.GenerativeModel("gemini-1.5-flash")

st.title("Fact Check Agent")

uploaded_file = st.file_uploader("Upload PDF", type="pdf")

def extract_text(pdf):
    reader = PdfReader(pdf)
    text = ""

    for page in reader.pages:
        text += page.extract_text()

    return text

def extract_claims(text):
    sentences = text.split(".")
    claims = []

    for sentence in sentences:
        if re.search(r'\d', sentence):
            claims.append(sentence.strip())

    return claims[:5]

def verify_claim(claim):
    prompt = f"""
    Verify this claim and tell whether it is True or False.
    Also provide the corrected fact.

    Claim:
    {claim}
    """

    response = model.generate_content(prompt)
    return response.text

if uploaded_file:
    st.success("PDF Uploaded")

    text = extract_text(uploaded_file)

    claims = extract_claims(text)

    st.subheader("Detected Claims")

    for claim in claims:
        st.write("### Claim")
        st.write(claim)

        result = verify_claim(claim)

        st.write("### Verification")
        st.write(result)

        st.divider()
