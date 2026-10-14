"""Find lexicon symptom phrases in free text.

The matcher is deliberately simple: exact phrase matching after light
normalisation, longest match wins, and a short look-back window for negation
cues. It is meant as a baseline and a test fixture, not a clinical NLP system.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

URGENCY_ORDER = {"emergency": 0, "same_day": 1, "routine": 2}

# Words that, shortly before a phrase, usually mean the symptom is denied.
NEGATION_CUES = {
    "en": {"no", "not", "without", "never", "denies", "deny", "none", "nor"},
    "de": {"kein", "keine", "keinen", "keiner", "keinem", "nicht", "ohne", "nie", "niemals"},
}
NEGATION_WINDOW = 4  # tokens before the phrase
CLAUSE_BREAK = re.compile(r"[.;:!?\n]|,\s*(?:but|aber|jedoch)\b|\b(?:but|aber|jedoch)\b")

_CONTRACTIONS = [
    (re.compile(r"\bcan'?t\b|\bcan not\b"), "cannot"),
    (re.compile(r"\bwon'?t\b"), "will not"),
    (re.compile(r"\bdon'?t\b"), "do not"),
    (re.compile(r"\bdoesn'?t\b"), "does not"),
    (re.compile(r"\bi'?m\b"), "i am"),
]


@dataclass(frozen=True)
class Concept:
    id: str
    label: dict[str, str]
    category: str
    urgency: str
    note: str
    phrases: dict[str, list[str]]


@dataclass(frozen=True)
class Match:
    concept_id: str
    urgency: str
    language: str
    phrase: str
    start: int
    end: int
    negated: bool

    def __str__(self) -> str:  # pragma: no cover - convenience only
        flag = " (negated)" if self.negated else ""
        return f"{self.concept_id} [{self.urgency}] '{self.phrase}'{flag}"


def normalise(text: str) -> str:
    """Lower-case, unify apostrophes, expand common contractions.

    Every replacement keeps character offsets stable except the contraction
    expansion, so the matcher maps offsets back through ``_offset_map``.
    """
    text = text.replace("’", "'").replace("‘", "'").casefold()
    for pattern, replacement in _CONTRACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _normalise_with_offsets(text: str) -> tuple[str, list[int]]:
    """Normalise ``text`` and return, for each output char, its source index."""
    out: list[str] = []
    offsets: list[int] = []
    # Normalise word by word so offsets can be tracked through expansions.
    for m in re.finditer(r"\S+|\s+", text):
        piece = m.group(0)
        norm = normalise(piece) if not piece.isspace() else piece
        out.append(norm)
        if len(norm) == len(piece):
            offsets.extend(range(m.start(), m.end()))
        else:
            # Expanded contraction: spread the output across the source span.
            span = m.end() - m.start()
            offsets.extend(m.start() + min(i, span - 1) for i in range(len(norm)))
    return "".join(out), offsets


@lru_cache(maxsize=1)
def load_lexicon() -> tuple[Concept, ...]:
    raw = json.loads(
        resources.files(__package__).joinpath("lexicon.json").read_text(encoding="utf-8")
    )
    return tuple(Concept(**c) for c in raw["concepts"])


@lru_cache(maxsize=1)
def _patterns() -> tuple[tuple[re.Pattern[str], Concept, str, str], ...]:
    compiled = []
    for concept in load_lexicon():
        for lang, phrases in concept.phrases.items():
            for phrase in phrases:
                body = r"\s+".join(re.escape(w) for w in normalise(phrase).split())
                compiled.append((re.compile(rf"(?<!\w){body}(?!\w)"), concept, lang, phrase))
    return tuple(compiled)


def _is_negated(norm_text: str, start: int, language: str) -> bool:
    before = norm_text[:start]
    breaks = list(CLAUSE_BREAK.finditer(before))
    if breaks:
        before = before[breaks[-1].end():]
    tokens = re.findall(r"\w+", before)[-NEGATION_WINDOW:]
    return any(t in NEGATION_CUES.get(language, set()) for t in tokens)


def find_symptoms(text: str, languages: tuple[str, ...] = ("en", "de")) -> list[Match]:
    """Return non-overlapping symptom matches in ``text``, in reading order.

    Where phrases overlap, the longest one wins, so "short of breath at rest"
    is reported as ``dyspnea_at_rest`` and not also as ``dyspnea``.
    """
    norm, offsets = _normalise_with_offsets(text)
    candidates = []
    for pattern, concept, lang, phrase in _patterns():
        if lang not in languages:
            continue
        for m in pattern.finditer(norm):
            candidates.append((m.start(), m.end(), concept, lang, phrase))

    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    kept = []
    last_end = -1
    for start, end, concept, lang, phrase in candidates:
        if start < last_end:
            # Overlaps a kept match; replace it only if this one is longer.
            prev = kept[-1]
            if end - start > prev[1] - prev[0]:
                kept[-1] = (start, end, concept, lang, phrase)
                last_end = end
            continue
        kept.append((start, end, concept, lang, phrase))
        last_end = end

    return [
        Match(
            concept_id=concept.id,
            urgency=concept.urgency,
            language=lang,
            phrase=text[offsets[start]: offsets[end - 1] + 1],
            start=offsets[start],
            end=offsets[end - 1] + 1,
            negated=_is_negated(norm, start, lang),
        )
        for start, end, concept, lang, phrase in kept
    ]


def highest_urgency(matches: list[Match]) -> str | None:
    """The most urgent level among non-negated matches, or ``None``."""
    levels = [m.urgency for m in matches if not m.negated]
    return min(levels, key=URGENCY_ORDER.__getitem__) if levels else None
