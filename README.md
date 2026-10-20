# DocuVerify prototype

**Team:** Fiza • Garry • Poorva  
**Concept:** Intelligent Document Verification  
**Core integration:** TinyFish Search + TinyFish Fetch

This is a working local prototype, not a production identity-verification service. It demonstrates a document-details workflow, live source discovery, page fetching, source-linked evidence, and a downloadable Claim Passport.

## 1. Requirements
- Python 3.10 or newer
- Internet connection
- TinyFish API key

TinyFish Search and Fetch API docs:
- https://docs.tinyfish.ai/search-api/
- https://docs.tinyfish.ai/fetch-api/

## 2. Run it (Windows)
1. Extract the ZIP folder.
2. Open the folder.
3. In the folder address bar in File Explorer, type `cmd` and press Enter.
4. Run these commands one by one:

```bash
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
```

5. Open `.env` in Notepad and replace `replace_with_your_own_key` with your TinyFish API key. Do not share the key or upload it to GitHub.
6. Run:

```bash
py -m streamlit run app.py
```

7. A browser tab should open with DocuVerify. If not, copy the local URL shown in the terminal (usually `http://localhost:8501`) into your browser.

## 3. Demo flow
1. Choose **Academic certificate** or **Transcript / marksheet**.
2. Enter an issuer such as a university or exam board.
3. Add an issue year or non-sensitive detail if useful.
4. Click **Verify with TinyFish**.
5. The app calls TinyFish Search, then tries TinyFish Fetch on up to three result URLs.
6. Review the evidence links and export the Claim Passport.

Use sample or consented documents. The uploaded PDF is read locally for text preview; the PDF itself is not sent to TinyFish. Names and reference numbers are excluded from the web query by default; only include them if you have permission and truly need them.

## 4. What is live and what is not?
- **Live:** TinyFish Search and Fetch calls, when a valid key is configured.
- **Prototype logic:** source triage, status text, and the Claim Passport summary.
- **Not included yet:** robust OCR for scanned PDFs, official issuer API integrations, cryptographic signature validation, identity matching, or an ML model trained on labelled genuine/fraudulent documents.
- Search results alone cannot prove a document is genuine. A missing result is not proof of fraud. A human reviewer should confirm records with the issuing organisation.

## 5. If something goes wrong
- **`TINYFISH_API_KEY not set`:** confirm the file is named `.env` (not `.env.txt`) and restart Streamlit.
- **API error / 401:** check the key in TinyFish dashboard and paste it without quotes or spaces.
- **No results:** broaden the issuer/document query.
- **PDF text preview empty:** the PDF may be a scan; enter document details manually. OCR is not enabled in this MVP.
- **Package install issue:** run `py -m pip install --upgrade pip` and retry `py -m pip install -r requirements.txt`.

## 6. Next improvements
- OCR for scanned pages, with on-device / private processing where possible
- issuer-specific verification adapters and signed records
- reviewer feedback and an evaluation set with labelled test cases
- audit logs, access controls, retention limits and privacy review
