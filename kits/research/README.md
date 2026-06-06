# Research Kit

Research and synthesis kit. Given a goal, decomposes it into sub-questions,
gathers sources, synthesizes findings, and produces a structured report.

## Usage

```bash
kando run kits/research --goal "Understand AI safety"
```

## Object types

| Type | Description |
|---|---|
| `Goal` | The top-level research goal |
| `Question` | A sub-question derived from the goal |
| `Source` | A reference or citation |
| `Finding` | An answer or insight for a question |
| `Synthesis` | A summary derived from all findings |

## Relation types

| Type | Direction | Meaning |
|---|---|---|
| `decomposes_into` | Goal → Question | Goal is broken into this question |
| `answers` | Finding → Question | Finding addresses this question |
| `synthesizes` | Synthesis → Goal | Synthesis summarises the goal's findings |
| `cites` | Finding → Source | Finding is backed by this source |

## Responder flow

1. `Goal` created → `on_goal_created` emits 3 default `Question` objects + `decomposes_into` relations
2. `Question` created → `on_question_created` emits a placeholder `Finding` + `answers` relation
3. All questions answered → `on_finding_created` detects coverage and emits `Synthesis` + `synthesizes` relation
