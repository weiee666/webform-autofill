---
name: web-form-autofill
description: >-
  Use when the user wants to fill in a web-based job-application form / careers
  portal (Shopee, Greenhouse, Lever, Workday, Workable, Breezy, ByteDance careers,
  AshbyHQ, etc.) using their stored personal info. The skill reads the user's
  maintained resume Excel (path remembered in a persistent config, asked once on first run),
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
2. **Data lives in a local Excel — never hardcoded.** The Excel path is remembered
   in a persistent config (`scripts/config.py`, stored under `$CLAUDE_PLUGIN_DATA`
   or `~/.config/webform-autofill`, surviving plugin updates). If it isn't set, ask
   the user **once**, save it, and never ask again. No path is hardcoded anywhere.
3. **Semantic match, not string match.** For each collected question, find the best
   answer in the Excel data by *meaning* (not exact label text). Surface anything
   ambiguous, sensitive, or judgment-based to the user.
4. **One-shot fill via a generated Playwright script.** Build the script from the
   actual fields/refs you saw in recon — never a fixed hardcoded template. Selectors
   and values come from *this* form. Fill everything in a single execution.
5. **Never submit.** After filling, stop, report "filled, not submitted", and ask the
   user to review and click Submit themselves.

---

## Step 0 — Resolve the Excel path (config, once — remembered forever)

The path is stored in a **persistent data dir that survives plugin updates**
(`$CLAUDE_PLUGIN_DATA`, else `~/.config/webform-autofill`), via `scripts/config.py`.

```bash
python3 scripts/config.py get        # prints the saved path, or empty
```

- **If it prints a path**, use it — do not ask the user.
- **If empty (first run)**, ask: *"你的简历信息 Excel 在哪？给我完整路径。"* Then save it:
  ```bash
  python3 scripts/config.py set "/path/to/your_resume.xlsx"
  ```
  Never ask again on later runs. Never hardcode a path in SKILL.md or `scripts/`.

## Step 1 — Refresh the resume cache

```bash
python3 scripts/dump_resume.py
```

This reads the saved Excel path automatically and writes the cache into the data dir
(`python3 scripts/config.py cachefile` prints its path). Re-dump every run — the user
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

## Performance rule (why the steps below look the way they do)

The slow path is **interacting with one control at a time** — every custom dropdown
done as `click-open → snapshot → click-option` is 3 LLM round-trips, and snapshotting
an *opened* dropdown can dump hundreds of options (e.g. a 254-country code list) into
one huge tool result. **Collapse work into scripts:** one recon script that harvests
*everything* (fields + every dropdown's options), then one fill script. Never click
dropdowns open one-by-one across separate tool calls.

## Step 2 — Recon: map the ENTIRE form in ONE script (don't click dropdowns one-by-one)

Navigate, then run a **single `browser_run_code_unsafe` script** that returns a
compact JSON inventory — do NOT lean on big `browser_snapshot` dumps. The script:

1. Lists every field: a stable selector (`data-test-id` / `name` / `id` / label),
   visible label, required (`*`), and type (text / textarea / select / combobox /
   radio / checkbox / file / date).
2. **Harvests every dropdown's options in the same pass**: for each custom combobox,
   open it, read the option texts, close it (Esc) — so you get
   `{ "Gender": ["Male","Female"], "Country of Residence": ["Singapore", ...], ... }`
   in ONE round-trip instead of 3 per dropdown. Radios/checkboxes: list their labels.
3. Returns one object: `{ fields:[...], options:{label:[...]}, multiStep:bool, nextButton:selector|null }`.

**If the form is multi-step** (Next / Continue / 下一步, or a step nav): repeat this
recon script per step until all steps are mapped. Build ONE inventory across all steps
before filling anything.

If you hit a login wall / SSO / CAPTCHA / OTP at any point, follow the **Login handoff**
protocol below.

## Login handoff — let the user log in, then resume

A login / SSO / CAPTCHA / OTP wall can appear at navigation or mid-fill. The Playwright
browser is a **real, visible window the user can take over**, so hand control to them
and resume in the same session:

1. **Stop.** Do **not** type the user's password, 2FA, or OTP yourself — credentials are
   the human's to enter (and entering them is a prohibited action regardless).
2. **Tell the user clearly**, e.g.:
   > "这一步需要登录。请在已经打开的浏览器窗口里完成登录（账号密码 / 验证码都你来操作），
   > 登录好之后跟我说一声『登录好了』，我接着填。"
3. **Wait.** Do not re-navigate, poll, or click in a loop while the user is logging in —
   that can disrupt their session. Just wait for their confirmation.
4. **When the user says they're logged in**, take a fresh snapshot to confirm you're past
   the wall (you see the form / dashboard, not the login page). If you're still on the
   login page, tell the user it didn't take and ask them to retry — don't proceed.
5. **Resume** from exactly where you left off (continue recon, or continue filling).

Constraints:
- The user must log in **in the Playwright-controlled window**, not their own separate
  browser — it's a different browser instance with its own session.
- Keep the browser session **alive** through the handoff. If it closes (tab goes blank),
  the login is lost and you must re-navigate and hand off again.

## Step 3 — Semantic match against the Excel data (incl. exact dropdown options)

- Consult `references/field_mapping.md` for the canonical ATS-label → JSON-key map
  and boilerplate (visa / availability / "how did you hear").
- For each field, pick the best answer from the cached `resume.json` (its path is
  `python3 scripts/config.py cachefile`) **by meaning**, not
  literal label (e.g. "Tell us about your AI experience" → the agent/LLM self-intro
  + relevant projects).
- For each dropdown, choose the **exact option string** from the harvested options
  list (so the fill script selects precisely, with no extra look-up round-trip).
- Mark as **ASK USER** (never guess): visa/eligibility, salary, availability dates,
  national ID / NRIC / passport, which resume PDF, and any free-text "why this company".
- Produce ONE fill-plan table (Field | Value | Source), flag ASK USER rows, confirm:
  > "下面是我准备填的内容，确认就开始填，要改的地方直接告诉我。"

## Step 4 — Fill in ONE shot with a generated Playwright script

After confirmation, generate a single `browser_run_code_unsafe` script **from this
form's actual selectors + the chosen exact values** (not a fixed template).

| Field type | How (use the exact value/option chosen in Step 3) |
|---|---|
| text / textarea | `page.fill(selector, value)` |
| custom dropdown | `getByRole('combobox',{name}).click()` → `getByRole('option',{name: <exact text>}).click()` |
| native `<select>` | `page.selectOption(selector, value)` |
| radio / checkbox | `getByRole('radio'/'checkbox',{name: <exact label>}).click()` |
| country / phone code | open once, pick the exact `(+65) Singapore`-style option |
| file upload | `page.locator('input[type=file]').nth(i).setInputFiles(path)` |

Script conventions:
- Each field in its own try/catch; **retry a failed field once**, then record
  `✗ <field>` and move on — **do not loop or stall** on a stubborn control.
- Return a per-field log (`✓`/`✗`) + total time. Don't re-snapshot mid-script.
- Multi-step: fill page 1 → click Next → fill page 2 … in one script (or one per step).
  **Never click the final Submit.**

## Step 4.5 — Hand stubborn fields back to the user

If a field **fails twice** (failed in Step 4 and again on a single targeted retry),
**stop fighting it.** List those fields with the exact value that should go in, and
tell the user to fill those few by hand. Don't spend more round-trips on them.

## Step 5 — Verify once + stop before Submit

- Take **one** final snapshot (not per-field) to confirm values landed.
- Report:
  ```
  ✅ 表单已填完，未提交。请人工检查后自行点 Submit。
     - 已填: <list>
     - 需你手填(自动填失败): <field> = <value>
     - 跳过 / 留空: <field> (<reason>)
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
- **Login / SSO / CAPTCHA / OTP**: use the **Login handoff** protocol — let the user
  log in in the browser window, wait for their "done", verify, then resume.
- **OS file pickers**: can't be driven; use `setInputFiles` on the `<input type=file>` directly.
- **Search-as-you-type country/phone dropdowns**: click, type `Singapore` or `65`,
  then click the option.
- **Free-text Q&A** ("Why this company?", "Tell us about your AI experience"): never
  boilerplate — draft fresh from the JD + recent projects, or hand a draft to the user.

## Anti-patterns

- ❌ Opening dropdowns one at a time across separate tool calls (`click → snapshot →
  click`). Harvest all options in the Step 2 recon script instead.
- ❌ Relying on big `browser_snapshot` dumps (an opened country list = hundreds of
  options). Extract a compact inventory with a script.
- ❌ Looping / stalling on one stubborn control. Retry once, then hand it to the user.
- ❌ Re-snapshotting after every field. Verify once at the end.
- ❌ Filling before you've surveyed the whole (multi-step) form.
- ❌ Hardcoding the Excel path, or re-asking for it (it's saved via `scripts/config.py`).
- ❌ Reusing a fixed/hardcoded Playwright selector template instead of generating
  from this form's recon.
- ❌ Auto-clicking Submit "because the user said fill it".
- ❌ Guessing visa / salary / availability / ID number / which resume without asking.
- ❌ Pasting a full ID / passport / family phone unless the form requires it AND the
  user okays it for this submission.
- ❌ Filling from stale data — always re-dump the resume cache first.
