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

## Workflow

1. **Config (once)** — the Excel path lives in `CLAUDE.md` (`RESUME_XLSX: <path>`).
   On first run the agent asks for it and writes it there; never hardcoded.
2. **Recon** — load the form and traverse *every* page of a multi-step form before
   filling, building a complete inventory of all questions.
3. **Semantic match** — map each question to the Excel data by meaning; flag
   ambiguous / sensitive fields for the user.
4. **One-shot fill** — generate a Playwright script *from this form's actual fields*
   (not a fixed template) and fill everything in one pass.
5. **Stop before Submit** — report what was filled and hand back for human review.

> Selectors are stable **per ATS** (e.g. SmartRecruiters `data-test-id="..."`), so the
> generated script's patterns reuse across that ATS's other postings.

## Setup

1. Put your resume data in your source Excel.
2. Set the path in `CLAUDE.md`:
   ```markdown
   ## Configuration
   RESUME_XLSX: /path/to/your_resume.xlsx
   ```
3. Refresh the cache:
   ```bash
   RESUME_XLSX="/path/to/your_resume.xlsx" python3 scripts/dump_resume.py
   ```
4. Point the agent at a careers-form URL; it surveys, fills, and stops before Submit.

## Privacy

`cache/resume.json` contains personal data (name, email, phone, ID number, address)
and is **git-ignored** — never commit it. Keep this repo's history free of personal data.

## Roadmap

- [x] Survey-the-whole-form-first + one-shot generated-script fill in `SKILL.md`
- [x] Excel path configurable via `CLAUDE.md` / `RESUME_XLSX` (no hardcoded path)
- [ ] `references/ats_selectors.md` — stable selectors per ATS (Greenhouse / Lever / SmartRecruiters / Workday)
- [ ] Optional standalone runner that replays a saved fill plan without an LLM

## License

MIT (personal project).
