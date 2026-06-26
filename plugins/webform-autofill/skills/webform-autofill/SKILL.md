---
name: web-form-autofill
description: >-
  Use when the user wants to fill in a web-based job-application form / careers
  portal (Shopee, Greenhouse, Lever, Workday, Workable, Breezy, ByteDance careers,
  AshbyHQ, etc.) using their stored personal info. The skill reads the user's
  maintained resume Excel (path stored in CLAUDE.md, asked once on first run),
  fully traverses the form first, semantically matches each question to the Excel
  data, fills everything in one Playwright pass, and stops before Submit so the
  user can review.
  Chinese triggers — 帮我填这个简历表 / 用我的信息填这个网申 / 填一下这个 careers 页 /
  把表单填完 / 这页要填的我帮你填掉 / 网申一下 / 填一下这个表 / 投这家公司. English triggers —
  autofill this application form / fill out this careers form / fill this job
  application / help me fill the Shopee/Lever/Workday form / submit my profile.
  Do NOT use for resume PDF generation (use the LaTeX template) or for adding
  projects to Excel (use the resume-project-writer skill).
---

# Web Form Autofill

Drive a browser-based job-application form to completion from the user's local
resume data: **survey the whole form first**, semantically match each question to
the Excel, fill it in **one Playwright pass**, and **stop before Submit** so a
human always reviews.

## Design principles (read first — these override anything below)

1. **Recon before fill.** Load the full page. If the form is multi-step, find the
   Next / Continue / 下一步 button and walk through *every* page, cataloguing every
   field and question first. Only after seeing the whole form do you start matching
   and filling.
2. **Data lives in a local Excel — never hardcoded.** The Excel path is read from
   this project's `CLAUDE.md`. If it isn't there, ask the user **once**, then write
   it into `CLAUDE.md` so you never ask again. No path is ever hardcoded in SKILL.md
   or the scripts.
3. **Semantic match, not string match.** For each collected question, find the best
   answer in the Excel data by *meaning* (not exact label text). Surface anything
   ambiguous, sensitive, or judgment-based to the user.
4. **One-shot fill via a generated Playwright script.** Build the script from the
   actual fields/refs you saw in recon — never a fixed hardcoded template. Selectors
   and values come from *this* form. Fill everything in a single execution.
5. **Never submit.** After filling, stop, report "filled, not submitted", and ask the
   user to review and click Submit themselves.

---

## Step 0 — Resolve the Excel path (config, once)

- Look in this project's `CLAUDE.md` for a `RESUME_XLSX: <path>` line under
  `## Configuration`.
- **If present**, use it.
- **If absent**, ask the user: *"你的简历信息 Excel 在哪？给我完整路径。"* Then append
  it to `CLAUDE.md`:
  ```markdown
  ## Configuration
  RESUME_XLSX: /path/to/your_resume.xlsx
  ```
  Do not ask again on later runs.
- Never hardcode a path in SKILL.md or in `scripts/`.

## Step 1 — Refresh the resume cache

Run the dump with the configured path:

```bash
RESUME_XLSX="<path from CLAUDE.md>" python3 scripts/dump_resume.py
```

This rebuilds `cache/resume.json` from the live Excel (re-dump every run — the user
keeps the Excel updated). The JSON shape:

```json
{
  "zh": {
    "基本信息": { "姓名": "...", "常用邮箱": "...", ... },
    "教育经历": [ {"_n": 1, "学历1-学校名称": "...", ...}, ... ],
    "实习经历": [ ... ],
    "工作经历": [ ... ],
    "项目经历": [ ... ],
    "链接": { "领英": "...", "github": "...", ... },
    "技能栈": { ... }
  },
  "en": { ... mirror structure with English values ... }
}
```

## Step 2 — Recon: traverse the ENTIRE form first (before filling anything)

1. `browser_navigate(url)` then `browser_snapshot()`.
2. Catalogue every field on the current page: visible label, required (`*`), type
   (text / textarea / dropdown / radio / checkbox / file upload / date picker), and
   its `ref`.
3. **If the form is multi-step** (Next / Continue / 下一步 buttons, or a step nav like
   Infineon's section list), walk through each step, snapshotting each, until you
   have seen **all** pages. Build ONE complete inventory of every question across all
   steps. Do not fill anything yet.
4. If you hit a login wall / CAPTCHA / SSO, **stop and hand back to the user** —
   Playwright can't get past these reliably.

Only when the whole form is mapped do you move on.

## Step 3 — Semantic match against the Excel data

- Consult `references/field_mapping.md` for the canonical ATS-label → JSON-key map
  and the boilerplate answers (visa / availability / "how did you hear").
- For each catalogued field, find the best answer in `cache/resume.json` **by
  meaning** — e.g. a box labelled "Tell us about your AI experience" maps to the
  agent/LLM self-intro + relevant projects, not a literal key.
- Mark these as **ASK USER** (never guess): visa/eligibility, salary, availability
  dates, national ID / NRIC / passport, which resume PDF to upload, and any
  free-text "why this company" box.
- Produce ONE readable fill-plan table (Field | Value | Source), flag the ASK USER
  rows, and get the user's confirmation:
  > "下面是我准备填的内容，确认就开始填，要改的地方直接告诉我。"

## Step 4 — Fill in ONE shot with a generated Playwright script

After confirmation, generate a `mcp__playwright__browser_run_code_unsafe` script
**from the actual fields you catalogued** — not a fixed template. The script adapts
to this form's real selectors/labels every time.

Field-type playbook (compose only what this form actually has):

| Field type | How |
|---|---|
| text / textarea | `page.fill(selector, value)` (prefer stable `data-test-id` / `name`; fall back to label) |
| custom dropdown | `getByRole('combobox', {name}).click()` → `getByRole('option', {name}).click()` |
| native `<select>` | `page.selectOption(selector, value)` |
| radio / checkbox | `getByRole('radio'/'checkbox', {name}).click()` |
| country / phone code | open combobox, pick by `(+65) Singapore` style label |
| file upload (resume) | `page.locator('input[type=file]').nth(i).setInputFiles(path)` |

Script conventions:
- Wrap each field in try/catch; push a `✓ name` / `✗ name: error` line; return the
  log + total time.
- For **multi-step** forms, fill page 1 → click Next → fill page 2 → … inside the
  script (or one script per step). **Never click the final Submit.**
- Re-snapshot after dropdowns if the form re-renders dependent fields.

## Step 5 — Stop before Submit + report

- Take a final snapshot to verify values landed.
- Report:
  ```
  ✅ 表单已填完，未提交。请人工检查后自行点 Submit。
     - 已填: <list>
     - 跳过 / 留空: <field> (<reason, e.g. need user input / intentionally blank>)
     - Resume 已上传: <PDF path>
  ```
- **Never click Submit.** The user reviews and submits themselves.

## Step 6 (optional) — Log the application

Only on explicit user request after they confirm they submitted: append a row to the
`跳转投递记录` sheet in the Excel (company, role, date, JD URL, status). Don't
pre-log a submission you didn't witness.

---

## Things to watch for

- **Forms that auto-populate from the uploaded resume** (Greenhouse, Workday): upload
  the resume during recon, snapshot again, then fill only the gaps + fix misparses.
- **Multi-step forms**: the recon (Step 2) must traverse all steps before filling.
- **CAPTCHAs / SSO / OS file pickers**: stop and hand back to the user.
- **Search-as-you-type country/phone dropdowns**: click, type `Singapore` or `65`,
  then click the option.
- **Free-text Q&A** ("Why this company?", "Tell us about your AI experience"): never
  boilerplate — draft fresh from the JD + recent projects, or hand a draft to the user.

## Anti-patterns

- ❌ Filling before you've surveyed the whole (multi-step) form.
- ❌ Hardcoding the Excel path in SKILL.md or scripts (it lives in `CLAUDE.md`).
- ❌ Reusing a fixed/hardcoded Playwright selector template instead of generating
  from this form's recon.
- ❌ Auto-clicking Submit "because the user said fill it".
- ❌ Guessing visa / salary / availability / ID number / which resume without asking.
- ❌ Pasting a full ID / passport / family phone unless the form requires it AND the
  user okays it for this submission.
- ❌ Filling from stale data — always re-dump `cache/resume.json` first.
