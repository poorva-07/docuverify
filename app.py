import os
import re
import requests
import streamlit as st
import streamlit as st
import os
from dotenv import load_dotenv


try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

load_dotenv()

st.set_page_config(
    page_title="DocuVerify | Evidence-led verification",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Soft sage UI ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --sage:#5f8067; --dark:#24392b; --muted:#6c7a6e; --cream:#f7faf4; --mint:#e7f0e3; --line:#dce6d8; }
html, body, [class*="css"] { font-family:'DM Sans', sans-serif; }
.stApp { background:var(--cream); color:var(--dark); }
[data-testid="stHeader"] { background:rgba(247,250,244,.94); }
.block-container { padding-top:1.35rem; max-width:1320px; }
h1,h2,h3 { font-family:'Manrope',sans-serif !important; color:var(--dark) !important; letter-spacing:-.035em; }
p, label, span { color:inherit; }
.hero { background:linear-gradient(110deg,#e7f0e3 0%,#f3f7ee 75%); border:1px solid #dce6d8; border-radius:24px; padding:26px 30px; margin-bottom:20px; }
.eyebrow { color:#5f8067; font-size:11px; letter-spacing:.14em; font-weight:800; text-transform:uppercase; }
.hero-title { font-family:'Manrope',sans-serif; font-size:38px; line-height:1.12; font-weight:800; color:#24392b; margin:8px 0 10px; }
.hero-sub { color:#637365; font-size:15px; max-width:750px; line-height:1.6; }
.pill { display:inline-block; padding:6px 10px; border-radius:999px; background:#fff; color:#4d7055; border:1px solid #dce6d8; font-size:11px; font-weight:700; margin-right:5px; }
.panel { background:white; border:1px solid #dce6d8; border-radius:18px; padding:20px 22px; margin-bottom:14px; }
.metric { background:white; border:1px solid #dce6d8; border-radius:15px; padding:15px 17px; min-height:92px; }
.metric-label { color:#718073; font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { color:#24392b; font-family:'Manrope',sans-serif; font-size:23px; font-weight:800; margin-top:5px; }
.source { background:white; border:1px solid #dce6d8; border-radius:14px; padding:15px 16px; margin:10px 0; }
.source-title { font-weight:700; font-size:15px; color:#24392b; margin-bottom:5px; }
.source-url { font-size:12px; color:#5f8067; overflow-wrap:anywhere; }
.source-snippet { font-size:13px; color:#6c7a6e; margin-top:8px; line-height:1.5; }
.small-note { color:#718073; font-size:12px; line-height:1.5; }
.stButton > button { border-radius:12px; border:1px solid #5f8067; background:#5f8067; color:white; font-weight:700; padding:.65rem 1rem; }
.stButton > button:hover { background:#45694d; border-color:#45694d; color:white; }
div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] div, div[data-testid="stTextArea"] textarea { border-radius:10px; }
section[data-testid="stSidebar"] { background:#edf4e9; border-right:1px solid #dce6d8; }
hr { border-color:#dce6d8; }
</style>
""", unsafe_allow_html=True)

TINYFISH_SEARCH = "https://api.search.tinyfish.ai"
TINYFISH_FETCH = "https://api.fetch.tinyfish.ai"

def api_key():
    return os.getenv("TINYFISH_API_KEY", "").strip()

def tinyfish_search(query, key):
    response = requests.get(
        TINYFISH_SEARCH,
        params={"query": query, "location": "IN", "language": "en"},
        headers={"X-API-Key": key, "Accept": "application/json"},
        timeout=35,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results", []) if isinstance(data, dict) else []
    clean = []
    for item in results[:8]:
        if not isinstance(item, dict):
            continue
        url = item.get("url") or item.get("link") or ""
        title = item.get("title") or item.get("site_name") or "Untitled source"
        snippet = item.get("snippet") or item.get("description") or "No preview was returned."
        if url:
            clean.append({"title": str(title), "url": str(url), "snippet": str(snippet), "site": str(item.get("site_name") or "")})
    return clean, data

def tinyfish_fetch(urls, key):
    if not urls:
        return []
    response = requests.post(
        TINYFISH_FETCH,
        headers={"X-API-Key": key, "Content-Type": "application/json", "Accept": "application/json"},
        json={"urls": urls[:4], "format": "markdown", "links": True},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        for k in ("results", "data", "pages", "items"):
            if isinstance(data.get(k), list):
                return data[k]
    return data if isinstance(data, list) else [{"content": str(data)}]

def officialish(url):
    u = url.lower()
    return any(x in u for x in (".gov.in", ".gov/", ".gov?", ".edu", ".ac.in", "digilocker", "ugc.gov", "cbse.gov", "nta.ac.in"))

def status_from_evidence(claims, sources, fetched):
    text = " ".join([s.get("title","") + " " + s.get("snippet","") + " " + s.get("url","") for s in sources]).lower()
    fetched_text = str(fetched).lower()
    combined = text + " " + fetched_text
    if not sources:
        return "Needs review", "TinyFish did not return usable source links. No authenticity conclusion can be made."
    issuer = claims.get("issuer", "").strip().lower()
    if issuer and issuer in combined:
        return "Evidence found", "At least one result appears related to the named issuer. A reviewer should confirm the exact record and document details."
    return "Needs review", "Relevant web sources were found, but this prototype cannot confirm the exact record from search results alone."

def read_pdf(upload):
    if not upload or PdfReader is None:
        return ""
    try:
        reader = PdfReader(upload)
        pages = []
        for page in reader.pages[:8]:
            pages.append(page.extract_text() or "")
        return "\n".join(pages).strip()
    except Exception:
        return ""

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 🌿 DocuVerify")
    st.caption("Evidence-led document checks")
    st.markdown("---")
    st.markdown("**Live connection**")
    if api_key():
        st.success("TinyFish key detected")
        st.caption("Search + Fetch are enabled.")
    else:
        st.warning("TinyFish key not set")
        st.caption("Add TINYFISH_API_KEY to your .env file to enable live verification.")
    st.markdown("---")
    st.markdown("**Prototype workflow**")
    st.markdown("1. Add document details\n2. Search live sources\n3. Review evidence links\n4. Export a Claim Passport")
    st.markdown("---")
    st.caption("Team: Fiza • Garry • Poorva")
    st.caption("Prototype only — not an official verification service.")
TINYFISH_API_KEY = (
    st.secrets.get("TINYFISH_API_KEY", "")
    or os.getenv("TINYFISH_API_KEY", "")
)

# ---------- Hero ----------
st.markdown("""
<div class="hero">
  <div class="eyebrow">Document trust, with evidence</div>
  <div class="hero-title">Looks real?<br>Let’s check the evidence.</div>
  <div class="hero-sub">DocuVerify helps reviewers compare document claims with live web information using TinyFish Search and Fetch. It explains what was found and what still needs a human check.</div>
  <div style="margin-top:16px">
    <span class="pill">TinyFish-powered</span><span class="pill">Source-linked</span><span class="pill">Human review</span>
  </div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1.02, 0.98], gap="large")

with left:
    st.markdown("### 01 &nbsp; Document details")
    st.markdown('<div class="small-note">For the demo, use a sample or non-sensitive document. Avoid entering private IDs unless you have permission to verify them.</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Attach a document (optional PDF)", type=["pdf"], help="PDF text is extracted locally when possible. The file itself is not uploaded to TinyFish by this prototype.")
    doc_type = st.selectbox("Document type", ["Academic certificate", "Transcript / marksheet", "Scholarship document", "Employment certificate", "Other"])
    issuer = st.text_input("Issuing organisation", placeholder="e.g. CBSE, university, training institute")
    holder = st.text_input("Name on document (optional)", placeholder="Use only if necessary")
    reference = st.text_input("Certificate / registration number (optional)", placeholder="Enter only if permitted")
    issue_date = st.text_input("Issue date / year (optional)", placeholder="e.g. 2025")
    extra = st.text_area("Any detail to check (optional)", placeholder="e.g. course title, campus, award name…", height=82)
    include_identifiers = st.checkbox("Include the name / reference number in the web query", value=False, help="Off by default to reduce sharing personal data with an external search service.")
    pdf_text = read_pdf(uploaded)
    if uploaded:
        st.caption(f"Attached: {uploaded.name} · {uploaded.size/1024:.0f} KB")
        if pdf_text:
            with st.expander("Preview extracted PDF text (processed locally)"):
                st.text(pdf_text[:3500])
        else:
            st.info("No selectable text was extracted. Scanned-PDF OCR is not enabled in this prototype; enter the details above manually.")
    run_live = st.button("🌱 Verify with TinyFish", use_container_width=True)

with right:
    st.markdown("### 02 &nbsp; What DocuVerify checks")
    st.markdown('<div class="panel"><b>Claim matching</b><br><span class="small-note">Compare issuer, document type, dates and optional reference details with source information.</span><hr><b>Live source discovery</b><br><span class="small-note">TinyFish Search finds current web pages; TinyFish Fetch reads selected pages as clean content.</span><hr><b>Evidence, not guesswork</b><br><span class="small-note">Each result includes its URL and a review note. Search results alone cannot prove a document is authentic.</span></div>', unsafe_allow_html=True)
    st.markdown("#### Verification stages")
    stages = [
        ("01", "Document details", "Ready when you provide an issuer or useful claim."),
        ("02", "TinyFish Search", "Discover potentially relevant pages."),
        ("03", "TinyFish Fetch", "Read selected pages for context."),
        ("04", "Claim Passport", "Summarise sources and outstanding checks.")
    ]
    for num, title, desc in stages:
        st.markdown(f'<div class="source"><span style="color:#5f8067;font-weight:800">{num}</span>&nbsp;&nbsp; <b>{title}</b><div class="small-note" style="margin-left:30px">{desc}</div></div>', unsafe_allow_html=True)

if run_live:
    if not issuer.strip() and not doc_type:
        st.error("Enter at least an issuing organisation or a document type.")
    elif not api_key():
        st.error("TinyFish is not connected yet. Set TINYFISH_API_KEY in your .env file, restart the app, and try again.")
        st.info("You can still show the UI to your team, but this button does not fabricate live results.")
    else:
        query_parts = [doc_type, "verification", issuer.strip()]
        if issue_date.strip():
            query_parts.append(issue_date.strip())
        if extra.strip():
            query_parts.append(extra.strip())
        if include_identifiers:
            if holder.strip():
                query_parts.append(holder.strip())
            if reference.strip():
                query_parts.append(reference.strip())
        query = " ".join(p for p in query_parts if p)
        with st.status("Checking live sources with TinyFish…", expanded=True) as status:
            st.write("Searching the live web for relevant issuer and document information.")
            try:
                sources, raw_search = tinyfish_search(query, api_key())
                st.write(f"TinyFish Search returned {len(sources)} source link(s).")
                urls = [s["url"] for s in sources[:3]]
                fetched = []
                if urls:
                    st.write("Fetching selected pages for cleaner source context.")
                    try:
                        fetched = tinyfish_fetch(urls, api_key())
                    except Exception as fetch_err:
                        st.warning(f"Search succeeded, but Fetch was unavailable: {fetch_err}")
                status.update(label="TinyFish search complete", state="complete", expanded=False)
                result_status, result_note = status_from_evidence({"issuer": issuer}, sources, fetched)
                st.session_state["last_verification"] = {
                    "query": query, "doc_type": doc_type, "issuer": issuer, "holder": holder if include_identifiers else "",
                    "reference": reference if include_identifiers else "", "issue_date": issue_date, "extra": extra,
                    "sources": sources, "fetched": fetched, "status": result_status, "note": result_note,
                }
            except requests.HTTPError as e:
                status.update(label="TinyFish returned an API error", state="error", expanded=True)
                st.error(f"TinyFish API error: {e}. Check your API key and account access.")
                try:
                    st.code(e.response.text[:1200])
                except Exception:
                    pass
            except Exception as e:
                status.update(label="Could not complete live verification", state="error", expanded=True)
                st.error(f"Something went wrong: {e}")

result = st.session_state.get("last_verification")
if result:
    st.markdown("---")
    st.markdown("## 03 &nbsp; Claim Passport")
    st.markdown('<div class="small-note">This is an evidence triage summary, not a certificate of authenticity. A human reviewer must confirm the exact record with the issuing organisation.</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f'<div class="metric"><div class="metric-label">Review status</div><div class="metric-value" style="font-size:20px">{result["status"]}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric"><div class="metric-label">Sources found</div><div class="metric-value">{len(result["sources"])}</div></div>', unsafe_allow_html=True)
    with c3:
        fetched_count = len(result.get("fetched") or [])
        st.markdown(f'<div class="metric"><div class="metric-label">Pages fetched</div><div class="metric-value">{fetched_count}</div></div>', unsafe_allow_html=True)
    st.info(result["note"])
    st.markdown("### Evidence sources")
    if result["sources"]:
        for idx, src in enumerate(result["sources"], start=1):
            label = "Likely official / institutional domain" if officialish(src["url"]) else "External source — check reliability"
            st.markdown(f"""
<div class="source">
  <div class="source-title">{idx}. {src['title']}</div>
  <div class="source-url"><a href="{src['url']}" target="_blank">{src['url']}</a></div>
  <div class="source-snippet">{src['snippet']}</div>
  <div style="margin-top:8px"><span class="pill">{label}</span></div>
</div>
""", unsafe_allow_html=True)
    else:
        st.warning("No usable links were returned. Try a broader issuer query.")
    with st.expander("Fetch results (TinyFish page context)"):
        if result.get("fetched"):
            st.json(result["fetched"])
        else:
            st.write("No fetched page content is available for this run.")
    passport_text = f"""DOCUVERIFY — CLAIM PASSPORT
Review status: {result['status']}
Document type: {result['doc_type']}
Issuer: {result['issuer']}
Issue date/year: {result['issue_date']}
Query used: {result['query']}

Review note:
{result['note']}

Evidence sources:
""" + "\n".join([f"- {s['title']}\n  {s['url']}\n  {s['snippet']}" for s in result["sources"]]) + """

IMPORTANT:
This is a prototype evidence-triage result, not an official verification or a finding of fraud.
A human reviewer should confirm the exact record with the issuing organisation.
"""
    st.download_button("↓ Export Claim Passport (.txt)", data=passport_text, file_name="docuverify_claim_passport.txt", mime="text/plain")
    if st.button("Clear current result"):
        st.session_state.pop("last_verification", None)
        st.rerun()

st.markdown("---")
st.markdown('<div class="small-note">DocuVerify • Team Fiza, Garry & Poorva • Prototype build • TinyFish Search + Fetch integration • Use sample documents for demos</div>', unsafe_allow_html=True)
