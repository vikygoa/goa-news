import os
import json
import feedparser
from google import genai

# 1. Fetch top Goa news items via RSS
RSS_URL = "https://news.google.com/rss/search?q=Goa+news&hl=en-IN&gl=IN&ceid=IN:en"
feed = feedparser.parse(RSS_URL)
raw_entries = feed.entries[:20]

news_input = []
for idx, entry in enumerate(raw_entries, 1):
    news_input.append(f"{idx}. Title: {entry.title}\nSummary: {entry.get('summary', '')}")

combined_text = "\n\n".join(news_input)

# 2. Call AI to rewrite and categorize
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

prompt = f"""
You are an editor for a clean, mobile-first, text-only daily Goa news digest.
Rewrite and summarize each of the following news stories in your own unique words to avoid any copyright issues.
Assign an appropriate short category tag (e.g., Civic, Tourism, Weather, Politics, Infrastructure, Sports, Crime).

Format strictly as a valid JSON array of objects with keys: "category", "headline", and "summary".

News items:
{combined_text}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config={"response_mime_type": "application/json"}
)

news_data = json.loads(response.text)

# 3. Generate mobile-friendly, responsive HTML
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Goa Top 20 News</title>
    <style>
        :root {{
            --bg: #ffffff;
            --text: #1a1a1a;
            --muted: #555555;
            --border: #e5e7eb;
            --badge-bg: #f3f4f6;
            --badge-text: #374151;
            --accent: #2563eb;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #0f172a;
                --text: #f8fafc;
                --muted: #94a3b8;
                --border: #1e293b;
                --badge-bg: #1e293b;
                --badge-text: #cbd5e1;
                --accent: #60a5fa;
            }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 20px 16px;
            max-width: 680px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}
        h1 {{ font-size: 1.5rem; font-weight: 800; }}
        .subtitle {{ font-size: 0.85rem; color: var(--muted); }}
        .item {{
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
        }}
        .tag {{
            display: inline-block;
            font-size: 0.75rem;
            font-weight: 600;
            background: var(--badge-bg);
            color: var(--badge-text);
            padding: 2px 8px;
            border-radius: 4px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }}
        .headline {{
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 6px;
            line-height: 1.4;
        }}
        .summary {{
            font-size: 0.92rem;
            color: var(--muted);
        }}
    </style>
</head>
<body>
    <header>
        <h1>Goa Top 20</h1>
        <p class="subtitle">Daily Automated Text Digest</p>
    </header>
    <main>
"""

for item in news_data:
    category = item.get("category", "General")
    headline = item.get("headline", "")
    summary = item.get("summary", "")
    
    html_content += f"""
        <article class="item">
            <span class="tag">{category}</span>
            <h2 class="headline">{headline}</h2>
            <p class="summary">{summary}</p>
        </article>
    """

html_content += """
    </main>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html updated successfully!")
