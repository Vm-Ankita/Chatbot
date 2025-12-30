python3 -m venv venv
source venv/bin/activate


pip install -r requirements.txt


ollama pull phi3:mini


python -m app.embed


uvicorn app.main:app --reload
