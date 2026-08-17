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
    raise RuntimeError("All models are currently busy. Please retry.")

news_data = json.loads(response.text)

# 3. Clean Inline SVG Category Icons
SVG_ICONS = {
    "Sports": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
    "Politics": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 22h16M2 10h20M12 2l8 6H4zM6 10v9M10 10v9M14 10v9M18 10v9"/></svg>',
    "Tourism": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>',
    "Weather": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/></svg>',
    "Crime": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "Civic": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/></svg>',
    "Entertainment": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 3 20 12 6 21 6 3"/></svg>',
    "Business": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
    "General": '<svg class="cat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
}

categories = ["All", "Sports", "Politics", "Tourism", "Weather", "Crime", "Civic", "Entertainment", "Business"]

category_pills_html = "".join([
    f'<button class="pill {"active" if cat == "All" else ""}" onclick="filterNews(\'{cat}\')">{SVG_ICONS.get(cat, "")} <span>{cat}</span></button>'
    for cat in categories
])

articles_html = ""
for item in news_data:
    cat = item.get("category", "General").strip().capitalize()
    if cat not in SVG_ICONS:
        cat = "General"
    
    headline = item.get("headline", "")
    summary = item.get("summary", "")
    icon_svg = SVG_ICONS.get(cat, SVG_ICONS["General"])
    
    articles_html += f"""
        <article class="card card-{cat.lower()}" data-category="{cat}">
            <div class="card-header">
                <span class="tag tag-{cat.lower()}">{icon_svg} {cat}</span>
            </div>
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
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --muted: #475569;
            --border: #e2e8f0;
            --badge-bg: #f1f5f9;
            --badge-text: #334155;
            --shadow: 0 2px 6px rgba(0,0,0,0.04);
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #0b0f19;
                --card-bg: #131b2e;
                --text: #f8fafc;
                --muted: #94a3b8;
                --border: #1e293b;
                --badge-bg: #1e293b;
                --badge-text: #cbd5e1;
                --shadow: 0 2px 8px rgba(0,0,0,0.3);
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
            margin-bottom: 16px;
        }}
        h1 {{ font-size: 1.7rem; font-weight: 900; letter-spacing: -0.5px; color: var(--text); }}
        .subtitle {{ font-size: 0.88rem; color: var(--muted); font-weight: 500; }}
        
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
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--card-bg);
            color: var(--badge-text);
            border: 1px solid var(--border);
            padding: 7px 14px;
            border-radius: 24px;
            font-size: 0.85rem;
            font-weight: 700;
            cursor: pointer;
            white-space: nowrap;
            box-shadow: var(--shadow);
            transition: all 0.2s ease;
        }}
        .pill.active {{
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
        }}
        .pill .cat-icon {{
            width: 14px;
            height: 14px;
        }}
        
        /* Modern Colorful Card Styles */
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 14px;
            border: 1px solid var(--border);
            border-left: 5px solid #94a3b8;
            box-shadow: var(--shadow);
            transition: transform 0.15s ease;
        }}
        .card:hover {{
            transform: translateY(-2px);
        }}
        .card.hidden {{
            display: none;
        }}
        
        /* Category specific border accents */
        .card-sports {{ border-left-color: #10b981; }}
        .card-politics {{ border-left-color: #ef4444; }}
        .card-tourism {{ border-left-color: #0ea5e9; }}
        .card-weather {{ border-left-color: #f59e0b; }}
        .card-crime {{ border-left-color: #8b5cf6; }}
        .card-entertainment {{ border-left-color: #ec4899; }}
        .card-business {{ border-left-color: #f97316; }}
        .card-civic {{ border-left-color: #64748b; }}
        
        .card-header {{
            margin-bottom: 8px;
        }}
        
        .tag {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 0.72rem;
            font-weight: 800;
            padding: 4px 9px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .tag .cat-icon {{
            width: 12px;
            height: 12px;
        }}
        
        /* Light pastel badge colors */
        .tag-sports {{ background: #dcfce7; color: #166534; }}
        .tag-politics {{ background: #fee2e2; color: #991b1b; }}
        .tag-tourism {{ background: #e0f2fe; color: #075985; }}
        .tag-weather {{ background: #fef3c7; color: #92400e; }}
        .tag-crime {{ background: #f3e8ff; color: #5b21b6; }}
        .tag-entertainment {{ background: #fce7f3; color: #9d174d; }}
        .tag-business {{ background: #ffedd5; color: #9a3412; }}
        .tag-civic {{ background: #f1f5f9; color: #334155; }}
        
        .headline {{
            font-size: 1.12rem;
            font-weight: 800;
            line-height: 1.4;
            margin-bottom: 8px;
            color: var(--text);
        }}
        .summary {{
            font-size: 0.94rem;
            color: var(--muted);
            line-height: 1.55;
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
                const btnText = btn.querySelector('span') ? btn.querySelector('span').innerText : btn.innerText;
                if (btnText.trim().toLowerCase() === selectedCategory.toLowerCase()) {{
                    btn.classList.add('active');
                }} else {{
                    btn.classList.remove('active');
                }}
            }});

            const items = document.querySelectorAll('.card');
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

print("index.html with colorful cards and bold headlines generated successfully!")
