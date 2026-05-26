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
    .badge-unverified { background: #d97706; c
