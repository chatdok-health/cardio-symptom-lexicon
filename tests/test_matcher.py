import pytest

from cardio_symptom_lexicon import find_symptoms, highest_urgency, load_lexicon
from cardio_symptom_lexicon.matcher import URGENCY_ORDER


def ids(text, **kwargs):
    return [m.concept_id for m in find_symptoms(text, **kwargs)]


def test_lexicon_is_well_formed():
    concepts = load_lexicon()
    seen = set()
    for c in concepts:
        assert c.id not in seen, f"duplicate id {c.id}"
        seen.add(c.id)
        assert c.urgency in URGENCY_ORDER
        assert set(c.label) == {"en", "de"}
        assert c.phrases["en"] and c.phrases["de"], c.id


def test_no_phrase_is_listed_under_two_concepts():
    owner = {}
    for c in load_lexicon():
        for lang, phrases in c.phrases.items():
            for p in phrases:
                key = (lang, p.casefold())
                assert key not in owner, f"{p!r} in {owner.get(key)} and {c.id}"
                owner[key] = c.id


@pytest.mark.parametrize(
    "text, expected",
    [
        ("I have had chest pain since this morning", ["chest_pain"]),
        ("Ich habe seit heute Morgen Brustschmerzen", ["chest_pain"]),
        ("My ankles are swollen and I gained 2 kg this week", ["rapid_weight_gain"]),
        ("Swollen ankles again, and I can't lie flat", ["edema", "orthopnea"]),
        ("Seit gestern Herzrasen und mir ist schwindelig", ["palpitations", "presyncope"]),
        ("I passed out in the kitchen", ["syncope"]),
    ],
)
def test_finds_symptoms(text, expected):
    assert ids(text) == expected


def test_longest_phrase_wins():
    assert ids("I am short of breath at rest") == ["dyspnea_at_rest"]


def test_curly_apostrophe_and_contraction():
    assert ids("I can’t catch my breath") == ["dyspnea"]


def test_offsets_point_at_original_text():
    text = "Since Monday I CAN'T LIE FLAT at night"
    (m,) = find_symptoms(text)
    assert text[m.start:m.end] == m.phrase == "CAN'T LIE FLAT"


def test_german_sharp_s_does_not_break_offsets():
    text = "Meine Füße sind dick, ich habe geschwollene Füße"
    (m,) = find_symptoms(text)
    assert m.phrase == "geschwollene Füße"


@pytest.mark.parametrize(
    "text",
    [
        "No chest pain today",
        "Keine Brustschmerzen mehr",
        "I have not fainted since the new tablets",
    ],
)
def test_negation(text):
    (m,) = find_symptoms(text)
    assert m.negated


def test_negation_stops_at_clause_break():
    matches = find_symptoms("No chest pain, but I feel dizzy")
    assert [(m.concept_id, m.negated) for m in matches] == [
        ("chest_pain", True),
        ("presyncope", False),
    ]


def test_highest_urgency_ignores_negated():
    assert highest_urgency(find_symptoms("No chest pain but always tired")) == "routine"
    assert highest_urgency(find_symptoms("Dizzy and then I fainted")) == "emergency"
    assert highest_urgency(find_symptoms("All good today")) is None


def test_language_filter():
    assert ids("Brustschmerzen and chest pain", languages=("de",)) == ["chest_pain"]
