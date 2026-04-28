import feedparser
import httpx
import hashlib
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from sqlalchemy.orm import Session
from . import models

BEHANCE_RSS = "https://www.behance.net/feeds/user?username={username}"

CATEGORY_KEYWORDS = {
    "mobile":   ["mobile", "ios", "android", "app", "iphone", "ipad"],
    "ux-ui":    ["ux", "ui", "interface", "dashboard", "web design", "saas", "wireframe"],
    "branding": ["brand", "identity", "logo", "visual identity", "branding", "rebrand"],
    "poster":   ["poster", "print", "typography", "type", "editorial"],
}

def guess_category(title: str, tags: list[str]) -> str:
    text = (title + " " + " ".join(tags)).lower()
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[cat] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "ux-ui"

def extract_cover(entry: dict) -> str | None:
    content = entry.get("content", [])
    for c in content:
        urls = re.findall(r'src=["\']([^"\']+project-cover[^"\']*)["\']', c.get("value", ""))
        if urls:
            return urls[0]
    summary = entry.get("summary", "")
    urls = re.findall(r'src=["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']', summary)
    if urls:
        return urls[0]
    return None

def extract_tags(entry: dict) -> list[str]:
    tags = []
    for t in entry.get("tags", []):
        term = t.get("term", "").strip().lower()
        if term:
            tags.append(term)
    return tags[:10]

def parse_date(entry: dict) -> datetime | None:
    for field in ("published", "updated"):
        val = entry.get(field)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                pass
    return None

def make_behance_id(url: str) -> str:
    m = re.search(r"/gallery/(\d+)/", url)
    if m:
        return m.group(1)
    return hashlib.md5(url.encode()).hexdigest()[:16]

def fetch_rss(username: str) -> list[dict]:
    url = BEHANCE_RSS.format(username=username)
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (compatible; curator/0.1)"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        return feed.entries
    except Exception as e:
        print(f"[RSS] Error fetching {username}: {e}")
        return []

def sync_designer(db: Session, designer_id: str, designer_name: str) -> int:
    username = designer_id
    entries = fetch_rss(username)
    added = 0

    for entry in entries:
        url = entry.get("link", "")
        if not url or "behance.net/gallery" not in url:
            continue

        behance_id = make_behance_id(url)
        existing = db.query(models.Project).filter_by(behance_id=behance_id).first()
        if existing:
            continue

        tags_raw = extract_tags(entry)
        title = entry.get("title", "Untitled")
        category = guess_category(title, tags_raw)

        project = models.Project(
            behance_id=behance_id,
            title=title,
            url=url,
            cover_url=extract_cover(entry),
            author_name=designer_name,
            author_id=designer_id,
            category=category,
            published_at=parse_date(entry),
            is_manual=False,
        )
        for tag_name in tags_raw:
            tag = db.query(models.Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = models.Tag(name=tag_name)
                db.add(tag)
                db.flush()
            project.tags.append(tag)

        db.add(project)
        added += 1

    db.commit()
    return added

def sync_all(db: Session) -> dict:
    follows = db.query(models.Follow).all()
    results = {}
    for follow in follows:
        count = sync_designer(db, follow.designer_id, follow.name)
        results[follow.designer_id] = count
        print(f"[RSS] {follow.name} (lvl {follow.level}): +{count} projects")
    return results
