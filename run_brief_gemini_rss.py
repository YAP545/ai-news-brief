"""AI brief using free RSS feeds + Gemini (no Search tool, 1 API request per run).
Setup:  pip install google-genai
        set GEMINI_API_KEY=your_google_key
Run:    python run_brief_gemini_rss.py
Optional: set GEMINI_MODEL=model-name   (default gemini-3.8-flash)
"""
import datetime as dt, email.utils, os, pathlib, re, urllib.request
import xml.etree.ElementTree as ET
from google import genai

FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "Ars Technica AI": "https://arstechnica.com/ai/feed/",
    "OpenAI": "https://openai.com/news/rss.xml",
    "Google AI": "https://blog.google/technology/ai/rss/",
    "Techmeme": "https://www.techmeme.com/feed.xml",
    "Hacker News (AI)": "https://hnrss.org/frontpage?q=AI+OR+LLM+OR+OpenAI+OR+Anthropic+OR+Gemini",
    "Inc42 (India)": "https://inc42.com/feed/",
}
WINDOW_HOURS = 36
here = pathlib.Path(__file__).parent
now = dt.datetime.now(dt.timezone.utc)

def parse_date(s):
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)

def clean(t, n=300):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", t).strip()[:n]

def first_text(f, *names):
    for n in names:
        if n in f and f[n].text:
            return f[n].text
    return ""

def parse_feed(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter():
        tag = it.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        f = {c.tag.split("}")[-1]: c for c in it}
        link = ""
        if "link" in f:
            link = f["link"].get("href") or (f["link"].text or "")
        items.append({
            "title": clean(first_text(f, "title"), 200),
            "link": link.strip(),
            "date": parse_date(first_text(f, "pubDate", "published", "updated", "date")),
            "summary": clean(first_text(f, "description", "summary", "content")),
        })
    return items

collected, failed = [], []
for name, url in FEEDS.items():
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 ai-brief"})
        data = urllib.request.urlopen(req, timeout=20).read()
        for it in parse_feed(data):
            if it["date"] and (now - it["date"]).total_seconds() <= WINDOW_HOURS * 3600:
                it["source"] = name
                collected.append(it)
    except Exception as e:
        failed.append(f"{name} ({type(e).__name__})")

collected.sort(key=lambda x: x["date"], reverse=True)
collected = collected[:80]
print(f"Collected {len(collected)} items from last {WINDOW_HOURS}h. Failed feeds: {failed or 'none'}")
if not collected:
    raise SystemExit("No items collected. Check your internet connection.")

lines = [f"- [{i['source']}] {i['title']} | {i['date']:%Y-%m-%d %H:%M} UTC | {i['link']} | {i['summary']}"
         for i in collected]
today = dt.date.today().strftime("%A, %B %d, %Y")
instructions = (here / "workflow" / "prompt.txt").read_text(encoding="utf-8").replace("{DATE}", today)

prompt = f"""{instructions}

IMPORTANT: You have no web access. Use ONLY the items listed below (collected from RSS feeds in the last {WINDOW_HOURS} hours).
Do not add facts from memory. Cluster duplicates by event, rank them, and write the brief in the required template.
If a section has no items, say so. Label single-source claims as such. Every item needs its link.

ITEMS:
{chr(10).join(lines)}
"""

key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not key:
    raise SystemExit("Set GEMINI_API_KEY first: set GEMINI_API_KEY=your_key")
client = genai.Client(api_key=key)
resp = client.models.generate_content(model=os.environ.get("GEMINI_MODEL", "gemini-3.8-flash"), contents=prompt)

note = f"\n\n---\n*Collected from RSS feeds. Failed feeds: {', '.join(failed) or 'none'}.*\n"
out = here / "brief" / f"ai_brief_{dt.date.today()}_rss.md"
out.write_text((resp.text or "") + note, encoding="utf-8")
print(f"Saved {out}")
