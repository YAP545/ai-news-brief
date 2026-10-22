import datetime, os, pathlib
from google import genai
from google.genai import types

here = pathlib.Path(__file__).parent
key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not key:
    raise SystemExit("Set GEMINI_API_KEY first: set GEMINI_API_KEY=your_key")

model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
today = datetime.date.today().strftime("%A, %B %d, %Y")
prompt = (here / "workflow" / "prompt.txt").read_text(encoding="utf-8").replace("{DATE}", today)

client = genai.Client(api_key=key)
resp = client.models.generate_content(
    model=model,
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())]
    ),
)

out = here / "brief" / f"ai_brief_{datetime.date.today()}_gemini.md"
out.write_text(resp.text or "", encoding="utf-8")
print(f"Saved {out}")