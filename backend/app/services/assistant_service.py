"""Phase 25 — a real-data-grounded question-answering assistant.

Deliberately NOT an LLM: no ANTHROPIC_API_KEY (or any other LLM API key)
is configured anywhere in this project, and adding one is a real cost/
external-service decision only the deploying user can make. This module
answers a small set of real, common questions ("which place is riskiest",
"is X safe", "how many alerts", "weather in X") entirely by querying the
real database — every fact in every answer is traceable to a real row.
No question this module doesn't recognize gets a guessed answer: an
unmatched question returns a clear "I can only answer..." message listing
what it actually supports, never a fabricated response.

`answer_question()` returns `{answer, intent, data}` — `data` carries the
real structured facts behind the natural-language `answer`, so a caller
(the frontend, or a test) can verify the prose isn't inventing anything
beyond what `data` actually contains.
"""
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.landslide_event import LandslideEvent
from app.models.zone import Zone

HELP_TEXT = (
    "I can answer real questions about this system's data: "
    "\"Which place/zone is riskiest?\" | "
    "\"Is <place> safe?\" or \"risk in <place>\" | "
    "\"How many active alerts?\" or \"which places have alerts?\" | "
    "\"Weather in <place>\" | "
    "\"How many landslides in <state>?\" "
    "I only ever answer from real data already in this system - I don't guess."
)

RISK_ORDER = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}


def _known_place_names(db: Session):
    """Real zone names/states, used to fuzzy-match a place mentioned in a
    question — never a hardcoded gazetteer, always whatever the database
    actually has right now."""
    rows = db.query(Zone.id, Zone.name, Zone.state).all()
    return rows


def _find_zone_by_name(db: Session, question: str) -> Optional[Zone]:
    """Matches a real zone by substring against its name or state, case-
    insensitive. Picks the longest matching name (most specific) if
    several real zones' names appear as substrings of the question."""
    q = question.lower()
    candidates = []
    for zone_id, name, state in _known_place_names(db):
        base_name = name.replace(" (Historical Cluster)", "")
        for candidate_text in (base_name, state):
            if candidate_text and candidate_text.lower() in q:
                candidates.append((len(candidate_text), zone_id))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    best_zone_id = candidates[0][1]
    return db.query(Zone).filter(Zone.id == best_zone_id).first()


def _zone_risk_sentence(zone: Zone) -> str:
    if zone.risk_level == "UNKNOWN":
        note = f" It has {zone.historical_event_count} real recorded historical landslide event(s)," if zone.historical_event_count else ""
        return (
            f"{zone.name} in {zone.state}: no real current risk score is available yet"
            f" (no real terrain/rainfall data is configured for this location).{note} "
            "This is disclosed honestly rather than showing a guessed score."
        )
    return (
        f"{zone.name} in {zone.state}: risk level {zone.risk_level}, "
        f"risk score {zone.risk_score:.1f}/100 (last updated {zone.updated_at.strftime('%d %b %Y, %H:%M') if zone.updated_at else 'unknown'})."
    )


def _handle_riskiest(db: Session, _question: str, top_n: int = 3) -> dict:
    zones = (
        db.query(Zone)
        .filter(Zone.risk_level != "UNKNOWN")
        .order_by(Zone.risk_score.desc())
        .limit(top_n)
        .all()
    )
    if not zones:
        return {
            "answer": "No zone currently has a real computed risk score - real terrain/rainfall data isn't configured anywhere yet.",
            "intent": "riskiest_place",
            "data": {"zones": []},
        }
    lines = [_zone_risk_sentence(z) for z in zones]
    answer = "Based on real, currently computed risk scores, the highest-risk place is:\n" + lines[0]
    if len(lines) > 1:
        answer += "\n\nNext highest:\n" + "\n".join(lines[1:])
    return {
        "answer": answer,
        "intent": "riskiest_place",
        "data": {"zones": [{"id": z.id, "name": z.name, "state": z.state, "risk_score": z.risk_score, "risk_level": z.risk_level} for z in zones]},
    }


def _handle_place_lookup(db: Session, question: str) -> dict:
    zone = _find_zone_by_name(db, question)
    if zone is None:
        return {
            "answer": "I couldn't match that to a real monitored zone. Check Data Sources or the Risk Map for the exact real zone/state names I know about.",
            "intent": "place_lookup",
            "data": {},
        }
    return {
        "answer": _zone_risk_sentence(zone),
        "intent": "place_lookup",
        "data": {"id": zone.id, "name": zone.name, "state": zone.state, "risk_score": zone.risk_score, "risk_level": zone.risk_level, "historical_event_count": zone.historical_event_count},
    }


def _handle_weather(db: Session, question: str) -> dict:
    zone = _find_zone_by_name(db, question)
    if zone is None:
        return {
            "answer": "I couldn't match that to a real monitored zone to look up weather for.",
            "intent": "weather_lookup",
            "data": {},
        }
    answer = (
        f"Real last-refreshed conditions for {zone.name}, {zone.state}: "
        f"{zone.rainfall_24h}mm rain in the last 24h, {zone.humidity}% humidity, {zone.temperature}C "
        f"(as of {zone.updated_at.strftime('%d %b %Y, %H:%M') if zone.updated_at else 'unknown'}). "
        "This is live data from Open-Meteo, refreshed periodically - not necessarily this exact second."
    )
    return {
        "answer": answer,
        "intent": "weather_lookup",
        "data": {"name": zone.name, "state": zone.state, "rainfall_24h": zone.rainfall_24h, "humidity": zone.humidity, "temperature": zone.temperature},
    }


def _handle_alerts(db: Session, _question: str) -> dict:
    active = db.query(Alert).filter(Alert.is_active.is_(True)).all()
    if not active:
        return {"answer": "There are no active alerts right now, based on real current zone risk data.", "intent": "alerts", "data": {"count": 0, "alerts": []}}
    lines = [f"{a.title} ({a.severity})" for a in active[:10]]
    more = f" (+{len(active) - 10} more)" if len(active) > 10 else ""
    return {
        "answer": f"There are {len(active)} real active alert(s):\n" + "\n".join(lines) + more,
        "intent": "alerts",
        "data": {"count": len(active), "alerts": [{"title": a.title, "severity": a.severity, "zone_id": a.zone_id} for a in active]},
    }


def _handle_state_event_count(db: Session, question: str) -> dict:
    zone = _find_zone_by_name(db, question)
    state = zone.state if zone else None
    if state is None:
        return {
            "answer": "I couldn't match that to a real Indian state in this system's data. Try naming the state directly.",
            "intent": "state_event_count",
            "data": {},
        }
    count = db.query(LandslideEvent).filter(LandslideEvent.state == state).count()
    return {
        "answer": f"{count} real historical landslide event(s) are recorded in {state} in this system's registered data (NASA Global Landslide Catalog, 1970-2016 snapshot - real events may have occurred outside that window/source that aren't reflected here).",
        "intent": "state_event_count",
        "data": {"state": state, "count": count},
    }


# Order matters: checked top-to-bottom, first match wins — "riskiest"
# and "alerts" are checked before the generic "safe"/"tell me about"
# place-lookup pattern so e.g. "which place is riskiest" doesn't fall
# through to a place-name fuzzy-match instead.
INTENT_PATTERNS = [
    (re.compile(r"\b(riskiest|highest.risk|most.risk|which (place|zone|area).{0,20}risk)", re.I), _handle_riskiest),
    (re.compile(r"\b(active alert|how many alert|which places? (have|has) alert)", re.I), _handle_alerts),
    (re.compile(r"\b(weather|rain|rainfall|temperature|humidity)\b", re.I), _handle_weather),
    (re.compile(r"\b(how many|number of).{0,10}(landslide|event)s?.{0,15}\bin\b", re.I), _handle_state_event_count),
    (re.compile(r"\b(safe|risk in|risk of|tell me about|how risky)\b", re.I), _handle_place_lookup),
]


def answer_question(db: Session, question: str) -> dict:
    question = (question or "").strip()
    if not question:
        return {"answer": HELP_TEXT, "intent": "help", "data": {}}

    for pattern, handler in INTENT_PATTERNS:
        if pattern.search(question):
            return handler(db, question)

    return {"answer": HELP_TEXT, "intent": "unrecognized", "data": {}}
