import os
import json
import time
import feedparser
from google import genai

# 1. Fetch from multiple Goa news & sports RSS feeds
FEEDS = [
    "https://news.google.com/rss/search?q=Goa+news&hl=en-IN&gl=IN&ceid=IN:en",
    "https://news.google.com/rss/search?q=Goa+sports+OR+Goa+football+OR+Goa+cricket&hl=en-IN&gl=IN&ceid=IN:en",
    "https://digitalgoa.com/feed/"
]

raw_articles = []
seen_titles = set()

for url in FEEDS:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        title = entry.title.strip()
        if title.lower() not in seen_titles:
            seen_titles.add(title.lower())
            raw_articles.append({
                "title": title,
                "summary": entry.get("summary", "")
            })

# Limit to top 50 unique items
raw_articles = raw_articles[:50]

news_input = []
for idx, entry in enumerate(raw_articles, 1):
    news_input.append(f"{idx}. Title: {entry['title']}\nContext: {entry['summary']}")

combined_text = "\n\n".join(news_input)

# 2. AI Summarization with Fallback & Retry Logic
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

prompt = f"""
You are an editor for a clean, mobile-first, text-only daily Goa news portal.
Rewrite and summarize each of the following news stories in your own unique, concise words (1-2 clear sentences).
Assign EXACTLY ONE of the following category tags to each item:
- Sports
- Politics
- Tourism
- Weather
- Crime
- Civic
- Entertainment
- Business

Format strictly as a valid JSON array of objects with keys: "category", "headline", and "summary".

News items to process:
{combined_text}
"""

# Models to try in order if one experiences high traffic
candidate_models = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]
response = None

for model_name in candidate_models:
    for attempt in range(2):
        try:
            print(f"Trying model: {model_name} (Attempt {attempt + 1})...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            break
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            time.sleep(3)
    if response:
        print(f"Successfully generated using {model_name}!")
        break

if not response:
    raise RuntimeError("All models are currently experiencing high demand. Please retry.")

news_data = json.loads(response.text)

# 3. Generate HTML with Interactive Filter Tabs
categories = ["All", "Sports", "Politics", "Tourism", "Weather", "Crime", "Civic", "Entertainment", "Business"]

category_pills_html = "".join([
    f'<button class="pill {"active" if cat == "All" else ""}" onclick="filterNews(\'{cat}\')">{cat}</button>'
    for cat in categories
])

articles_html = ""
for item in news_data:
    cat = item.get("category", "Civic").strip()
    headline = item.get("headline", "")
    summary = item.get("summary", "")
    
    articles_html += f"""
        <article class="item" data-category="{cat}">
            <span class="tag tag-{cat.lower()}">{cat}</span>
            <h2 class="headline">{headline}</h2>
            <p class="summary">{summary}</p>
        </article>
    """

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Goa Top 50 Daily News</title>
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
            padding: 16px;
            max-width: 680px;
            margin: 0 auto;
        }}
        header {{
            border-bottom: 2px solid var(--border);
            padding-bottom: 12px;
            margin-bottom: 14px;
        }}
        h1 {{ font-size: 1.6rem; font-weight: 800; }}
        .subtitle {{ font-size: 0.85rem; color: var(--muted); }}
        
        .filter-bar {{
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 12px;
            margin-bottom: 16px;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }}
        .filter-bar::-webkit-scrollbar {{ display: none; }}
        
        .pill {{
            background: var(--badge-bg);
            color: var(--badge-text);
            border: 1px solid var(--border);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: 0.2s ease;
        }}
        .pill.active {{
            background: var(--text);
            color: var(--bg);
            border-color: var(--text);
        }}
        
        .item {{
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
        }}
        .item.hidden {{
            display: none;
        }}
        .tag {{
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            background: var(--badge-bg);
            color: var(--badge-text);
            padding: 2px 8px;
            border-radius: 4px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }}
        .tag-sports {{ background: #dcfce7; color: #15803d; }}
        .tag-politics {{ background: #fee2e2; color: #b91c1c; }}
        .tag-tourism {{ background: #e0f2fe; color: #0369a1; }}
        .tag-weather {{ background: #fef9c3; color: #a16207; }}
        .tag-crime {{ background: #f3e8ff; color: #6b21a8; }}
        
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
        <h1>Goa Top 50</h1>
        <p class="subtitle">Daily Automated Digest &middot; Fast Text News</p>
    </header>

    <div class="filter-bar">
        {category_pills_html}
    </div>

    <main id="news-container">
        {articles_html}
    </main>

    <script>
        function filterNews(selectedCategory) {{
            const buttons = document.querySelectorAll('.pill');
            buttons.forEach(btn => {{
                if (btn.innerText === selectedCategory) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});

            const items = document.querySelectorAll('.item');
            items.forEach(item => {{
                const itemCat = item.getAttribute('data-category');
                if (selectedCategory === 'All' || itemCat.toLowerCase() === selectedCategory.toLowerCase()) {{
                    item.classList.remove('hidden');
                }} else {{
                    item.classList.add('hidden');
                }}
            }});
        }}
    </script>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("index.html updated successfully!")
