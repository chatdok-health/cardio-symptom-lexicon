# Cardio Symptom Lexicon

**How patients actually describe cardiovascular symptoms, in English and German.**

Patients rarely say "orthopnoea" or "paroxysmal nocturnal dyspnoea". They say *"I need more pillows to breathe at night"* or *"Ich wache nachts auf und bekomme keine Luft"*. This lexicon maps everyday phrases like these to cardiovascular symptom concepts. Each concept has an urgency level, so that health chatbots, triage tools and research pipelines can recognise red-flag symptoms in free text.

It is maintained by [ChatDok](https://chatdok.com) and comes from our work on conversational support for people with heart disease.

> ⚠️ **Not a medical device.** This lexicon is a research and engineering resource. It does not replace clinical judgement or local escalation protocols, and simple phrase matching will miss many ways of describing a symptom.

## What's inside

| | |
|---|---|
| [`cardio_symptom_lexicon/lexicon.json`](cardio_symptom_lexicon/lexicon.json) | 18 symptom concepts with English and German labels, patient-language phrases, a category and an urgency level |
| [`cardio_symptom_lexicon/matcher.py`](cardio_symptom_lexicon/matcher.py) | A small, dependency-free baseline matcher with longest-match and negation handling |

### Concepts

| Category | Concepts |
|---|---|
| Pain | chest pain, leg pain when walking (claudication) |
| Breathing | breathlessness, breathlessness at rest, when lying flat, waking at night breathless, night cough, pink frothy sputum |
| Fluid | swelling of legs and ankles, rapid weight gain |
| Rhythm | palpitations |
| Consciousness | fainting, dizziness |
| Stroke (FAST) | face drooping, arm weakness, speech difficulty |
| Bleeding | serious bleeding (relevant for anticoagulant users) |
| General | fatigue |

### Urgency levels

| Level | Meaning |
|---|---|
| `emergency` | Call emergency services now (112 in the EU) |
| `same_day` | Contact the care team or a doctor today |
| `routine` | Mention at the next contact, or sooner if new or getting worse |

The levels follow widely published patient guidance for heart disease and stroke, such as the FAST stroke signs and heart-failure warning signs. They are deliberately conservative and are **not** a substitute for the escalation rules of a specific care programme.

## Usage

```bash
pip install git+https://github.com/chatdok-health/cardio-symptom-lexicon
```

```python
from cardio_symptom_lexicon import find_symptoms, highest_urgency

matches = find_symptoms("No chest pain, but I can't lie flat and I have swollen ankles")
for m in matches:
    print(m.concept_id, m.urgency, repr(m.phrase), "negated" if m.negated else "")
# chest_pain emergency 'chest pain' negated
# orthopnea same_day "can't lie flat"
# edema routine 'swollen ankles'

print(highest_urgency(matches))  # same_day
```

Each `Match` holds the concept id, its urgency, the language, the matched text, character offsets in the original string, and a `negated` flag.

You can also use the JSON file directly from any language.

## Limitations

- **Exact phrases only.** Word order changes ("my ankles are swollen" compared with "swollen ankles"), typos and paraphrases are not matched. Use the lexicon as seed vocabulary or as test data for a more robust model.
- **Simple negation.** A negation word (such as *no*, *not*, *kein*, *nicht*) within four words before the phrase, in the same clause, marks the match as negated. Double negatives, hypotheticals ("what if I get chest pain?") and past history are not handled.
- **No severity or timing.** "Mild chest ache last year" matches the same concept as "crushing chest pain now".
- **Two languages.** Contributions in other languages are welcome.

## Contributing

Add phrases you have seen patients use, in any language, with the concept they belong to. Please never add text copied from real patient conversations. Paraphrase it instead. See the [contributing guide](https://github.com/chatdok-health/.github/blob/main/CONTRIBUTING.md).

Run the tests with:

```bash
python -m pytest
```

## License

Code: [Apache 2.0](LICENSE). The lexicon data (`lexicon.json`) is also available under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Please credit "ChatDok GmbH".
