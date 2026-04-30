from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from . import models

# weights
W_TAGS      = 40.0
W_DESIGNER  = 35.0
W_SOCIAL    = 25.0

# social sub-weights
W_FOLLOW1   = 25.0
W_FOLLOW2   = 10.0

# awards bonuses (added on top, max 100)
AWARD_ADOBE     = 25.0
AWARD_FEATURED  = 15.0
AWARD_APPRECIATED = 10.0

# time decay thresholds
DECAY_90  = 0.5   # likes older than 90 days
DECAY_180 = 0.2   # likes older than 180 days

def _time_weight(liked_at: datetime) -> float:
    age = datetime.utcnow() - liked_at
    if age > timedelta(days=180):
        return DECAY_180
    if age > timedelta(days=90):
        return DECAY_90
    return 1.0

def _build_tag_weights(db: Session) -> dict[str, float]:
    """
    For every liked project, collect its tags weighted by time decay.
    Returns {tag_name: weight} normalised to [0..1].
    """
    likes = db.query(models.Like).all()
    tag_scores: dict[str, float] = defaultdict(float)

    for like in likes:
        project = like.project
        if not project:
            continue
        tw = _time_weight(like.liked_at)
        for tag in project.tags:
            tag_scores[tag.name] += tw

    if not tag_scores:
        return {}

    max_score = max(tag_scores.values())
    return {tag: score / max_score for tag, score in tag_scores.items()}

def _build_designer_weights(db: Session) -> dict[str, float]:
    """
    For every liked project, give the author a reputation score (time-decayed).
    Returns {author_id: weight} normalised to [0..1].
    """
    likes = db.query(models.Like).all()
    designer_scores: dict[str, float] = defaultdict(float)

    for like in likes:
        project = like.project
        if not project:
            continue
        tw = _time_weight(like.liked_at)
        designer_scores[project.author_id] += tw

    if not designer_scores:
        return {}

    max_score = max(designer_scores.values())
    return {did: score / max_score for did, score in designer_scores.items()}

def _build_follow_set(db: Session) -> tuple[set[str], set[str]]:
    """
    Returns (level1_designer_ids, level2_designer_ids).
    """
    follows = db.query(models.Follow).all()
    lvl1 = {f.designer_id for f in follows if f.level == 1}
    lvl2 = {f.designer_id for f in follows if f.level == 2}
    return lvl1, lvl2

def score_project(
    project: models.Project,
    tag_weights: dict[str, float],
    designer_weights: dict[str, float],
    lvl1: set[str],
    lvl2: set[str],
) -> float:
    # 1. tag score
    tag_score = 0.0
    if tag_weights and project.tags:
        matched = [tag_weights.get(tag.name, 0.0) for tag in project.tags]
        if matched:
            tag_score = min(sum(matched) / len(matched) + max(matched) * 0.5, 1.0)
    tag_score *= W_TAGS

    # 2. designer score
    designer_score = designer_weights.get(project.author_id, 0.0) * W_DESIGNER

    # 3. social graph score
    social_score = 0.0
    if project.author_id in lvl1:
        social_score += W_FOLLOW1
    elif project.author_id in lvl2:
        social_score += W_FOLLOW2

    # 4. awards bonus
    award_bonus = 0.0
    if project.awards == "adobe_award":
        award_bonus = AWARD_ADOBE
    elif project.awards == "featured":
        award_bonus = AWARD_FEATURED
    elif project.awards == "appreciated":
        award_bonus = AWARD_APPRECIATED

    raw = tag_score + designer_score + social_score
    # normalise to 0-100, then add award bonus on top
    max_possible = W_TAGS + W_DESIGNER + W_FOLLOW1
    base = raw / max_possible * 100
    return round(min(base + award_bonus, 100), 1)

def recalculate_all(db: Session) -> dict:
    """
    Recalculate scores for all projects and persist to DB.
    Returns summary stats.
    """
    tag_weights     = _build_tag_weights(db)
    designer_weights = _build_designer_weights(db)
    lvl1, lvl2      = _build_follow_set(db)

    projects = db.query(models.Project).all()
    if not projects:
        return {"updated": 0, "avg_score": 0}

    scores = []
    for project in projects:
        s = score_project(project, tag_weights, designer_weights, lvl1, lvl2)
        project.score = s
        scores.append(s)

    db.commit()

    return {
        "updated": len(projects),
        "avg_score": round(sum(scores) / len(scores), 1),
        "max_score": round(max(scores), 1),
        "min_score": round(min(scores), 1),
        "tag_signals": len(tag_weights),
        "designer_signals": len(designer_weights),
    }

def recalculate_one(db: Session, project_id: int) -> float:
    """
    Recalculate score for a single project (e.g. right after a like).
    """
    project = db.query(models.Project).get(project_id)
    if not project:
        return 0.0

    tag_weights      = _build_tag_weights(db)
    designer_weights = _build_designer_weights(db)
    lvl1, lvl2       = _build_follow_set(db)

    s = score_project(project, tag_weights, designer_weights, lvl1, lvl2)
    project.score = s
    db.commit()
    return s
