# College Chatbot

Simple Streamlit-based chatbot that uses local site scraping and Mistral LLM integration to answer questions about the college.

Quick start (Windows):

1. Create and activate a virtual environment:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
streamlit run app.py
```

See `run_command.txt` for a copyable command sequence.

Files of interest:
- `app.py` — Streamlit frontend
- `college_bot.py` — Scraper and chatbot logic
- `knowledge_base.json` — Local knowledge store (created/updated by the bot)
