import requests
import json
import time
import re
import os
from datetime import datetime
from collections import Counter

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

JOURNALS = [
    {"name": "Computers & Education", "issn": "0360-1315"},
    {"name": "British Journal of Educational Technology", "issn": "1467-8535"},
    {"name": "Educational Technology Research and Development", "issn": "1042-1629"},
    {"name": "Journal of Computer Assisted Learning", "issn": "1365-2729"},
    {"name": "Computers in Human Behavior", "issn": "0747-5632"},
    {"name": "Internet and Higher Education", "issn": "1096-7516"},
    {"name": "Interactive Learning Environments", "issn": "1049-4820"},
    {"name": "Learning and Instruction", "issn": "0959-4752"},
    {"name": "Education and Information Technologies", "issn": "1360-2357"},
    {"name": "Journal of Educational Computing Research", "issn": "0735-6331"},
    {"name": "International Journal of Human-Computer Interaction", "issn": "1044-7318"},
    {"name": "Early Childhood Education Journal", "issn": "1082-3301"},
    {"name": "Early Childhood Research Quarterly", "issn": "0885-2006"},
    {"name": "Journal of Early Childhood Research", "issn": "1476-718X"},
]

KEYWORD_QUERIES = [
    "artificial intelligence early childhood",
    "AI child development",
    "machine learning young children education",
    "generative AI learning education",
    "ChatGPT education student",
    "large language model education",
    "educational robot children preschool",
    "cognitive development technology children",
    "computational thinking early childhood",
    "screen time child development",
    "game-based learning early childhood",
    "adaptive learning preschool",
    "natural language processing children",
    "augmented reality early education",
    "intelligent tutoring system early childhood",
    "executive function technology children",
    "working memory digital learning",
    "voice assistant children learning",
    "tablet young children education",
    "metacognition AI learning",
]

RESEARCH_DIRECTIONS = [
    {
        "id": "ai_tools",
        "name": "AI工具与教育应用",
        "subtitle": "AI Tools in Education",
        "icon": "🤖",
        "keywords": ["ChatGPT", "GPT", "LLM", "large language model", "generative AI", "artificial intelligence", "machine learning", "deep learning"],
    },
    {
        "id": "cognitive",
        "name": "认知发展与学习科学",
        "subtitle": "Cognitive Development & Learning Science",
        "icon": "🧠",
        "keywords": ["cognitive development", "executive function", "working memory", "attention", "metacognition", "cognitive load", "self-regulation"],
    },
    {
        "id": "robots",
        "name": "机器人与智能交互代理",
        "subtitle": "Robots & Intelligent Interactive Agents",
        "icon": "💬",
        "keywords": ["robot", "chatbot", "conversational agent", "voice assistant", "intelligent tutoring", "dialogue system"],
    },
    {
        "id": "digital_media",
        "name": "数字媒体与屏幕使用",
        "subtitle": "Digital Media & Screen Time",
        "icon": "📱",
        "keywords": ["screen time", "tablet", "digital media", "digital learning", "digital technology", "mobile"],
    },
    {
        "id": "game_learning",
        "name": "游戏化与自适应学习",
        "subtitle": "Game-based & Adaptive Learning",
        "icon": "🎮",
        "keywords": ["game-based", "gamification", "adaptive learning", "personalized learning", "game", "play"],
    },
    {
        "id": "ar_vr",
        "name": "增强现实与虚拟现实",
        "subtitle": "AR / VR in Early Education",
        "icon": "🥽",
        "keywords": ["augmented reality", "virtual reality", "AR", "VR", "immersive", "mixed reality"],
    },
    {
        "id": "early_literacy",
        "name": "早期读写与数学能力",
        "subtitle": "Early Literacy & Early Math",
        "icon": "📚",
        "keywords": ["early literacy", "early math", "language development", "reading", "writing", "numeracy", "vocabulary"],
    },
    {
        "id": "social_emotional",
        "name": "社会情感发展",
        "subtitle": "Social-Emotional Development",
        "icon": "❤️",
        "keywords": ["social-emotional", "social emotional", "emotion", "empathy", "social development", "wellbeing"],
    },
    {
        "id": "computational",
        "name": "计算思维与编程教育",
        "subtitle": "Computational Thinking & Coding",
        "icon": "💻",
        "keywords": ["computational thinking", "coding", "programming", "computer science", "algorithm"],
    },
    {
        "id": "family_school",
        "name": "家校技术整合",
        "subtitle": "Technology Integration at Home & School",
        "icon": "🏫",
        "keywords": ["parent", "teacher", "family", "home learning", "classroom", "school", "preschool teacher"],
    },
]

CROSSREF_BASE = "https://api.crossref.org/journals"
SS_BASE = "https://api.semanticscholar.org/graph/v1/paper/search"
USER_EMAIL = "jiawengou0912@gmail.com"


def strip_html(text):
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()


def fetch_with_retry(url, params, retries=3, delay=3):
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=30)
            if resp.status_code == 429:
                wait = delay * (2 ** attempt)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise e
    return None


def fetch_journal_papers(journal, limit=5):
    url = f"{CROSSREF_BASE}/{journal['issn']}/works"
    params = {
        "sort": "published",
        "order": "desc",
        "rows": limit,
        "select": "title,abstract,DOI,author,published-print,published-online,URL",
        "mailto": USER_EMAIL,
    }
    try:
        resp = fetch_with_retry(url, params)
        if not resp:
            return []
        items = resp.json().get("message", {}).get("items", [])
        papers = []
        for item in items:
            title = item.get("title", [""])[0] if item.get("title") else ""
            if not title:
                continue
            abstract = strip_html(item.get("abstract", ""))
            doi = item.get("DOI", "")
            authors = []
            for a in item.get("author", [])[:3]:
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if name:
                    authors.append(name)
            pub_date = ""
            pub = item.get("published-print") or item.get("published-online")
            if pub:
                parts = pub.get("date-parts", [[]])[0]
                pub_date = "-".join(str(p) for p in parts)
            papers.append({
                "title": title,
                "abstract": abstract if abstract else "Abstract not available via CrossRef. Click title to view the paper.",
                "doi": doi,
                "url": f"https://doi.org/{doi}" if doi else item.get("URL", ""),
                "authors": authors,
                "published": pub_date,
                "journal": journal["name"],
                "venue": journal["name"],
            })
        return papers
    except Exception as e:
        print(f"    Error: {e}")
        return []


def fetch_keyword_papers(query, limit=5):
    params = {
        "query": query,
        "fields": "title,abstract,year,authors,venue,publicationDate,externalIds",
        "limit": limit,
    }
    try:
        resp = fetch_with_retry(SS_BASE, params)
        if not resp:
            return []
        papers = []
        for item in resp.json().get("data", []):
            authors = [a.get("name", "") for a in item.get("authors", [])[:3]]
            doi = item.get("externalIds", {}).get("DOI", "")
            pid = item.get("paperId", "")
            papers.append({
                "paperId": pid,
                "title": item.get("title", ""),
                "abstract": item.get("abstract") or "Abstract not available.",
                "authors": authors,
                "venue": item.get("venue", ""),
                "published": item.get("publicationDate") or str(item.get("year", "")),
                "url": f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{pid}",
                "query": query,
            })
        return papers
    except Exception as e:
        print(f"    Error: {e}")
        return []


def extract_hot_topics(all_papers):
    results = []
    for direction in RESEARCH_DIRECTIONS:
        count = 0
        found_keywords = []
        for paper in all_papers:
            text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
            matched = [kw for kw in direction["keywords"] if kw.lower() in text]
            if matched:
                count += 1
                for kw in matched:
                    if kw not in found_keywords:
                        found_keywords.append(kw)
        if count > 0:
            results.append({
                "id": direction["id"],
                "name": direction["name"],
                "subtitle": direction["subtitle"],
                "icon": direction["icon"],
                "count": count,
                "keywords": found_keywords[:5],
            })
    return sorted(results, key=lambda x: x["count"], reverse=True)


def generate_digest(all_papers):
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("  No GROQ_API_KEY, skipping digest")
        return None

    candidates = [
        p for p in all_papers
        if p.get("title") and p.get("abstract")
        and p["abstract"] not in ("Abstract not available.", "Abstract not available via CrossRef. Click title to view the paper.")
    ][:55]

    lines = []
    for p in candidates:
        venue = p.get("venue") or p.get("journal", "")
        title = p.get("title", "")
        abstract = (p.get("abstract", "") or "")[:160]
        lines.append(f"[{venue}] {title}\n{abstract}")

    papers_str = "\n---\n".join(lines)

    prompt = f"""你是一位专注于AI与幼儿发展、教育技术学的学术研究助理。

以下是今天从14本核心SSCI期刊和关键词检索获取的最新学术论文：

{papers_str}

请基于这些论文，用中文生成一份简洁的研究资讯简报，格式如下：

📌 今日核心动态
（2至3句，概括今天整体研究趋势和主要关注点）

🔥 热点研究方向
（列出3至4个具体方向，每个方向说明：研究者正在研究什么、有哪些发现或争议、对研究者的启示）

💡 值得关注的新兴方向
（1至2个刚出现或交叉创新的方向，说明为什么值得跟进）

要求：语言简洁专业，直接面向研究者，读完能知道今天可以关注什么、可以做什么研究。直接输出内容，不要解释格式。"""

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "max_tokens": 1200,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        print(f"  Digest generated ({len(content)} chars)")
        return content
    except Exception as e:
        print(f"  Digest error: {e}")
        return None


def main():
    result = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "digest": None,
        "journal_papers": {},
        "keyword_papers": [],
        "hot_topics": [],
    }

    print("Fetching journal papers via CrossRef...")
    for journal in JOURNALS:
        print(f"  {journal['name']}")
        papers = fetch_journal_papers(journal, limit=5)
        result["journal_papers"][journal["name"]] = papers
        time.sleep(0.5)

    print("\nFetching keyword papers via Semantic Scholar...")
    seen_ids = set()
    for query in KEYWORD_QUERIES:
        print(f"  {query}")
        papers = fetch_keyword_papers(query, limit=5)
        for p in papers:
            pid = p.get("paperId") or p.get("title", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                result["keyword_papers"].append(p)
        time.sleep(3)

    print("\nExtracting hot topics...")
    all_papers = result["keyword_papers"].copy()
    for papers in result["journal_papers"].values():
        all_papers.extend(papers)
    result["hot_topics"] = extract_hot_topics(all_papers)

    print("\nGenerating AI research digest...")
    result["digest"] = generate_digest(all_papers)

    with open("papers.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    kw_count = len(result["keyword_papers"])
    print(f"\nDone! {kw_count} keyword papers | Updated: {result['updated_at']}")


if __name__ == "__main__":
    main()
