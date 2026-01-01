python3 -m venv venv
source venv/bin/activate


pip install -r requirements.txt


ollama pull phi3:mini


python -m app.embed


uvicorn app.main:app --reload



🔧 STEP 2 — INSTALL OCR DEPENDENCIES (ONE TIME ONLY)

OCR is needed only during ingestion, not during chat.

2.1 Install system dependency
sudo apt update
sudo apt install -y tesseract-ocr

Verify:

tesseract --version

2.2 Install Python libraries (inside venv)
pip install pytesseract pillow




rm -rf .chroma
python -m app.embed
uvicorn app.main:app --reload
