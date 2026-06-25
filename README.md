# webform-autofill

An agent-driven assistant that fills web-based **job-application / careers forms**
(Greenhouse, Lever, Workday, Workable, SmartRecruiters, ByteDance/Shopee careers, etc.)
from a single maintained spreadsheet of personal data, and **stops before final
submission** so a human always reviews.

## Why

Filling the same personal info into dozens of ATS forms is tedious and error-prone.
This tool reads your resume data once, plans which value goes into which field,
drives a real browser to fill them, and hands control back to you for the Submit click.

## How it works

```
Excel (personal data)  ──dump──►  cache/resume.json
                                        │
page snapshot  ──►  field mapping  ──►  fill plan  ──►  browser fills form  ──►  STOP before Submit
```

- **`SKILL.md`** — the agent workflow (snapshot → plan → fill → stop-before-submit).
- **`scripts/dump_resume.py`** — rebuilds `cache/resume.json` from the source Excel.
- **`references/field_mapping.md`** — canonical mapping from common ATS field names
  to resume fields, plus boilerplate answers (visa / availability / "how did you hear").

## Fill strategies

| Strategy | Speed | When |
|---|---|---|
| Step-by-step (snapshot → click → select) | slow, adaptive | unfamiliar form, first pass |
| Batched Playwright script (`run_code`) | fast (seconds) | structure already known |
| Standalone `.spec.js` + node | fastest, deterministic | same ATS, repeated use |

> Selectors are stable **per ATS** (e.g. SmartRecruiters `data-test-id="..."`), so a
> script written for one Infineon posting reuses across Infineon's other postings.

## Setup

1. Maintain your personal data in the source Excel (path configured in `dump_resume.py`).
2. Run the dump to refresh the cache:
   ```bash
   python3 scripts/dump_resume.py
   ```
3. Point the agent at a careers-form URL; it fills and stops before Submit.

## Privacy

`cache/resume.json` contains personal data (name, email, phone, ID number, address)
and is **git-ignored** — never commit it. Keep this repo's history free of personal data.

## Roadmap

- [ ] Bake the batched-script fast path into `SKILL.md`
- [ ] `references/ats_selectors.md` — stable selectors per ATS (Greenhouse / Lever / SmartRecruiters / Workday)
- [ ] Make the Excel path configurable (env var / config) instead of hardcoded
- [ ] Optional standalone runner that replays a saved fill plan without an LLM

## License

MIT (personal project).
