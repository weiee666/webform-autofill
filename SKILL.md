---
name: web-form-autofill
description: >-
  Use when the user wants to fill in a web-based job-application form / careers
  portal (Shopee, Greenhouse, Lever, Workday, Workable, Breezy, ByteDance careers,
  AshbyHQ, etc.) using their stored personal info. The skill reads the user's
  maintained resume Excel (path via the RESUME_XLSX env var),
  drives Playwright MCP to inspect the page, plans which value goes into which
  field, fills the form, and stops before Submit so the user can review.
  Chinese triggers — 帮我填这个简历表 / 用我的信息填这个网申 / 填一下这个 careers 页 /
  把表单填完 / 这页要填的我帮你填掉 / 网申一下 / 填一下这个表 / 投这家公司. English triggers —
  autofill this application form / fill out this careers form / fill this job
  application / help me fill the Shopee/Lever/Workday form / submit my profile.
  Do NOT use for resume PDF generation (use the LaTeX template) or for adding
  projects to Excel (use the resume-project-writer skill).
---

# Web Form Autofill

Drive a browser-based job application form to completion using the user's
stored personal data, stopping before final submission.

## Core principles

1. **Never click Submit.** Stop at the last step and show the user what's about
   to be sent. The whole point of this skill is to save typing while keeping
   final review human-controlled.
2. **Plan before clicking.** Snapshot the form, propose a complete fill plan
   (every field → which value, every dropdown → which option, every upload →
   which file path), get user confirmation, then execute.
3. **Surface ambiguity.** If a field could match multiple sources (e.g. two
   emails, two phone numbers, English vs Chinese name), ask the user which to
   use. Do not silently guess.
4. **Never paste sensitive data unprompted.** Full ID numbers, passport
   numbers, salary expectations, references' phone numbers — only fill if the
   form explicitly asks AND the user okays it for this application.

## Workflow

### Step 1 — Refresh the resume cache

Run the dump script. It rebuilds `cache/resume.json` from the live Excel. This
should be done every time the skill runs because the user maintains the Excel
across sessions (new projects, updated phone, etc.).

```bash
python3 scripts/dump_resume.py
```

The script outputs a summary line per language. The JSON has this shape:

```json
{
  "zh": {
    "基本信息": { "姓名": "...", "常用邮箱": "...", ... },
    "教育经历": [ {"_n": 1, "学历1-学校名称": "Nanyang Technological University", ...}, ... ],
    "实习经历": [ ... ],
    "工作经历": [ ... ],
    "项目经历": [ ... ],
    "链接": { "领英": "...", "github": "...", ... },
    "技能栈": { ... }
  },
  "en": { ... mirror structure with English values ... }
}
```

### Step 2 — Read the field mapping reference

```
Read: references/field_mapping.md
```

This contains the canonical mapping from common ATS field names to JSON keys,
plus boilerplate answers for visa / availability / "how did you hear" style
questions. Always consult this before improvising.

### Step 3 — Confirm which job folder this is for

Ask the user (or infer from recent context) which `已投递公司/NN_<company>_<role>/`
folder this application corresponds to. That folder contains:

- `<Name>_resume.pdf` — the file to upload for the "Resume*" field
- (sometimes) a cover letter

If no role-specific folder exists yet, ask whether to build one first (the
right resume PDF improves the application meaningfully).

### Step 4 — Open the form and snapshot it

```
mcp__playwright__browser_navigate(url=<application_url>)
mcp__playwright__browser_snapshot()
```

The snapshot is an accessibility tree. Read every form field. For each field
note: the visible label, whether it's required (`*`), type (text / textarea /
dropdown / file upload / date picker), and the `ref=eNNN` so you can target
it later.

### Step 5 — Build a fill plan

Cross-reference the snapshot against `cache/resume.json` and the field
mapping. Produce a single readable table for the user before touching the
form. Example:

```
| Field                  | Value                                        | Source                       |
|------------------------|----------------------------------------------|------------------------------|
| First Name*            | <given name>                                 | derived (姓名)               |
| Last Name*             | <family name>                                | derived (姓名)               |
| Email*                 | <school email>                               | en.基本信息.常用邮箱2        |
| Contact Number*        | <SG mobile>                                  | 基本信息.手机号1             |
| Current Location*      | Singapore                                    | mapping default              |
| Education 1 — School*  | <university>                                 | en.教育经历[0].学历1-学校名称|
| ...                    | ...                                          | ...                          |
| Resume upload*         | 已投递公司/<NN_company_role>/<Name>_resume.pdf | latest job folder          |
| Visa sponsorship*      | Yes — EP for full-time / no for intern       | field_mapping boilerplate    |
| Availability period    | <ASK USER — confirm window>                  | needs confirmation           |
```

Mark anything ambiguous with **ASK USER**. Then literally ask:

> "下面是我准备填的内容，确认就开始填，要改的地方直接告诉我。"

### Step 6 — Fill the form

After confirmation, execute. Prefer `mcp__playwright__browser_fill_form` for
batching text fields; use `mcp__playwright__browser_click` +
`browser_select_option` for dropdowns; use `mcp__playwright__browser_file_upload`
for file fields.

After each meaningful section (Personal Info → Education → Experience →
Other Information), take a fresh snapshot and verify the values landed
correctly. ATS forms commonly re-render fields when a dropdown changes —
don't assume earlier fills are still intact.

### Step 7 — Final review

Take a final snapshot. Report:

```
✅ 表单已填完，未提交。请人工检查后点 Submit。
   - 已填: First Name, Last Name, Email, Contact, Location, Education 1, 
           Experience 1 (Tenth Global), Experience 2 (Bank), Skills (5), 
           LinkedIn URL, Visa sponsorship, Availability
   - 跳过 / 留空: CGPA (need user input), Expected Salary (intentionally blank),
                  Transcript file (need user input)
   - Resume 已上传: <PDF path>
```

Do **not** click Submit. The user clicks Submit themselves after reviewing.

### Step 8 (optional) — Log the application

If the user confirms they've submitted, append a row to the `跳转投递记录`
sheet in the Excel (company name, role, date, JD URL, status). Do this only
on explicit user request — don't pre-log a submission you didn't witness.

## Things to watch for

- **Forms that auto-populate from uploaded resume.** Many ATS systems
  (Greenhouse, Workday) parse the uploaded PDF and pre-fill fields, then let
  the user edit. In that case: upload the resume first, snapshot again, fill
  only the gaps + correct any misparses.
- **Multi-step forms.** Some platforms split into pages (Personal → Resume →
  Q&A → Review). After each "Next" click, snapshot again and resume from
  Step 5.
- **CAPTCHAs / SSO logins / file pickers.** Stop and ask the user to handle
  these — Playwright can't get past them reliably.
- **Country / phone dropdowns.** These often use search-as-you-type. Click,
  type `Singapore` or `65`, then click the option.
- **Custom Q&A boxes** (e.g. "Why this company?", "Tell us about your AI
  experience"). Do NOT use boilerplate. Either draft fresh based on the JD
  and the user's recent projects, or hand back to the user with a draft.

## Anti-patterns

- ❌ Filling the form silently without showing the plan first.
- ❌ Auto-clicking Submit "because the user said fill it".
- ❌ Guessing visa / salary / availability without asking.
- ❌ Pasting full ID numbers / passport numbers / family contact phones
  unless the form requires them AND the user okays it for this submission.
- ❌ Hardcoding values that should come from `cache/resume.json` (the user
  updates the Excel — always re-dump).
