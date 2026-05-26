import streamlit as st
import pdfplumber
import google.generativeai as genai
import requests
import json
import os

# ── Config ──────────────────────────────────────────────────────────────────
genai.configure(api_key="AIzaSyBm5ekx-Mrft2H-5ZxpMC5BOyqb2wAZzCQ")
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="FactCheck Agent", page_icon="🔍", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; background: #0a0a0f; color: #e8e6f0; }
.stApp { background: #0a0a0f; }
.hero { text-align: center; padding: 3rem 0 2rem; }
.hero h1 { font-size: 3.5rem; font-weight: 800; letter-spacing: -2px; background: linear-gradient(135deg, #c084fc, #818cf8, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
.hero p { color: #6b7280; font-size: 1.1rem; margin-top: 0.5rem; font-family: 'DM Mono', monospace; }
.verdict-card { border-radius: 12px; padding: 1.2rem 1.5rem; margin: 0.75rem 0; border-left: 4px solid; font-family: 'DM Mono', monospace; font-size: 0.88rem; line-height: 1.6; }
.verdict-true  { background: #052e16; border-color: #16a34a; color: #bbf7d0; }
.verdict-false { background: #2d0a0a; border-color: #dc2626; color: #fecaca; }
.verdict-unverified { backgrou
