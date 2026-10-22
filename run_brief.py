"""Daily AI brief via Anthropic API + web search tool.
Usage: ANTHROPIC_API_KEY=... python run_brief.py
Requires: pip install anthropic
Schedule (weekdays 8am): 0 8 * * 1-5 /usr/bin/python3 /path/run_brief.py
"""
import datetime, pathlib, anthropic

here = pathlib.Path(__file__).parent
today = datetime.date.today().strftime("%A, %B %d, %Y")
prompt = (here / "workflow" / "prompt.txt").read_text().replace("{DATE}", today)

client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=4000,
    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 20}],
    messages=[{"role": "user", "content": prompt}],
)
text = "\n".join(b.text for b in msg.content if b.type == "text")
out = here / "brief" / f"ai_brief_{datetime.date.today()}.md"
out.write_text(text)
print(f"Saved {out}")
# Optional: post to Slack/email here.
