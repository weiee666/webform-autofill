# webform-autofill

> A Claude Code **plugin marketplace** (`weiee-plugins`) distributing one plugin
> (`webform-autofill`) that bundles a Skill. See [Install as a Claude Code plugin](#install-as-a-claude-code-plugin).

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
2. On first use the agent asks for the Excel path **once** and remembers it (stored
   under `$CLAUDE_PLUGIN_DATA` or `~/.config/webform-autofill`, surviving plugin
   updates). To set it yourself:
   ```bash
   python3 scripts/config.py set "/path/to/your_resume.xlsx"
   ```
3. Refresh the cache (reads the saved path automatically):
   ```bash
   python3 scripts/dump_resume.py
   ```
4. Point the agent at a careers-form URL; it surveys, fills, and stops before Submit.

> Config & cache live in the data dir (`python3 scripts/config.py datadir`), not in
> the repo — so nothing personal is committed and the path persists across updates.

## Privacy

`cache/resume.json` contains personal data (name, email, phone, ID number, address)
and is **git-ignored** — never commit it. Keep this repo's history free of personal data.

## Install as a Claude Code plugin

This repo is both a **marketplace** and a single **plugin**:

```
.claude-plugin/marketplace.json                 # marketplace catalog (weiee-plugins)
plugins/webform-autofill/
├── .claude-plugin/plugin.json                  # plugin manifest
└── skills/webform-autofill/                     # the bundled Skill
    ├── SKILL.md  ├── scripts/  └── references/
```

**Local (development)** — add the repo directory, no push needed:
```text
/plugin marketplace add /path/to/webform-autofill
/plugin install webform-autofill@weiee-plugins
/reload-plugins
```

**From GitHub (after pushing)**:
```text
/plugin marketplace add weiee666/webform-autofill
/plugin install webform-autofill@weiee-plugins
```

Manage: `/plugin list`, `/plugin marketplace update weiee-plugins`,
`/plugin disable webform-autofill@weiee-plugins`.

> After editing the skill, run `/plugin marketplace update weiee-plugins` then
> `/reload-plugins` — installed plugins are **copied** into `~/.claude/plugins/cache/`,
> so live repo edits don't apply until you update.

## Roadmap

- [x] Survey-the-whole-form-first + one-shot generated-script fill in `SKILL.md`
- [x] Excel path configurable via `CLAUDE.md` / `RESUME_XLSX` (no hardcoded path)
- [x] Packaged as a Claude Code plugin marketplace
- [x] Persistent config (`scripts/config.py`) under `$CLAUDE_PLUGIN_DATA` / `~/.config/webform-autofill` — Excel path remembered once, survives plugin updates
- [x] Login handoff: pause at a login/SSO/CAPTCHA wall, let the user log in, resume on their "done"
- [ ] `references/ats_selectors.md` — stable selectors per ATS (Greenhouse / Lever / SmartRecruiters / Workday) to shortcut recon on repeat platforms
- [ ] Optional standalone runner that replays a saved fill plan without an LLM

> Not doing: a persistent browser profile. Each company is a separate account; you log
> in once per site (and save credentials in your own password manager), so a shared
> profile adds no value and only stores cookies on disk.

## License

MIT (personal project).
