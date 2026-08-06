import requests
import json
import time
import re
from datetime import datetime
from collections import Counter

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

HOT_TOPIC_KEYWORDS = [
    "ChatGPT", "GPT-4", "GPT", "LLM", "large language model", "generative AI",
    "machine learning", "deep learning", "neural network", "artificial intelligence",
    "robot", "chatbot", "conversational agent", "voice assistant",
    "preschool", "kindergarten", "early childhood", "toddler",
    "cognitive development", "executive function", "working memory", "attention",
    "screen time", "tablet", "digital learning", "digital media",
    "game-based", "adaptive learning", "personalized learning",
    "computational thinking", "coding", "programming",
    "augmented reality", "virtual reality", "AR", "VR",
    "metacognition", "self-regulation", "social-emotional",
    "language development", "early literacy", "early math",
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
    counts = Counter()
    for paper in all_papers:
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        for kw in HOT_TOPIC_KEYWORDS:
            if kw.lower() in text:
                counts[kw] += 1
    return [{"topic": t, "count": c} for t, c in counts.most_common(15) if c > 0]


def main():
    result = {
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
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

    with open("papers.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    kw_count = len(result["keyword_papers"])
    print(f"\nDone! {kw_count} keyword papers | Updated: {result['updated_at']}")


if __name__ == "__main__":
    main()
