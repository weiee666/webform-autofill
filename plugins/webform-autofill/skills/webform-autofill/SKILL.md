---
name: web-form-autofill
description: >-
  Use when the user wants to fill in a web-based job-application form / careers
  portal (Shopee, Greenhouse, Lever, Workday, Workable, Breezy, ByteDance careers,
  AshbyHQ, etc.) using their stored personal info. The skill reads the user's
  maintained resume Excel (path remembered in a persistent config, asked once on first run),
  fully traverses the form first, semantically matches each question to the Excel
  data, fills everything in one batch via the agent-browser CLI, and stops before
  Submit so the user can review.
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
the Excel, fill it in **one batch**, and **stop before Submit** so a human reviews.

## Browser tooling — use the agent-browser CLI

Drive the browser with the **`agent-browser` CLI** (Vercel Labs, native Rust).
It is just shell commands, so call it with Bash — no MCP.

- **Primary: `agent-browser`** handles ~90% of forms (`open --headed`, `snapshot`,
  `fill`, `select`, `check`, `upload`, `click @ref`, `batch`, `find role ...`).
- **Fallback: Playwright CLI** only for the rare hard case the CLI can't express
  (exotic widgets, deep JS). Reach for it only after agent-browser genuinely can't.
- **Do NOT use the Playwright MCP** (`browser_*` tools). It's deprecated for this skill.

Two facts that make the whole flow work:
- **Headed window**: `agent-browser open <url> --headed` shows a real browser the
  user can take over (needed for the login handoff).
- **Persistent session**: a background daemon keeps the same browser alive across
  separate CLI calls, so `open` → (user logs in) → `snapshot` → `fill` all share one
  session. `agent-browser close` (or `close --all`) ends it.

If you're unsure of a command, run `agent-browser skills get core --full` — the CLI
ships its own version-matched usage guide.

## Design principles (read first — these override anything below)

1. **Recon before fill.** Load the full page. If the form is multi-step, walk through
   *every* page first, cataloguing every field and question. Only after seeing the
   whole form do you start matching and filling.
2. **Data lives in a local Excel — never hardcoded.** The Excel path is remembered
   in a persistent config (`scripts/config.py`, under `$CLAUDE_PLUGIN_DATA` or
   `~/.config/webform-autofill`, surviving plugin updates). If unset, ask the user
   **once**, save it, never ask again.
3. **Semantic match, not string match.** For each question, find the best answer in
   the Excel data by *meaning* (not exact label). Surface ambiguous / sensitive /
   judgment fields to the user.
4. **One-shot fill via `agent-browser batch`.** Build the batch from the actual refs
   you saw in recon + the exact values chosen — never a fixed template.
5. **Never submit.** After filling, stop, report "filled, not submitted", and let the
   user review and click Submit.

---

## Step 0 — Resolve the Excel path (config, once — remembered forever)

```bash
python3 scripts/config.py get        # prints the saved path, or empty
```

- **If it prints a path**, use it — do not ask the user.
- **If empty (first run)**, ask: *"你的简历信息 Excel 在哪？给我完整路径。"* Then save it:
  ```bash
  python3 scripts/config.py set "/path/to/your_resume.xlsx"
  ```
  Never ask again. Never hardcode a path in SKILL.md or `scripts/`.

## Step 1 — Refresh the resume cache

```bash
python3 scripts/dump_resume.py
```

Reads the saved Excel path automatically and writes the cache into the data dir
(`python3 scripts/config.py cachefile` prints its path). Re-dump every run. Shape:

```json
{
  "zh": {
    "基本信息": { "姓名": "...", "常用邮箱": "...", ... },
    "教育经历": [ {"_n": 1, "学历1-学校名称": "...", ...}, ... ],
    "实习经历": [ ... ], "工作经历": [ ... ], "项目经历": [ ... ],
    "链接": { "领英": "...", "github": "...", ... }, "技能栈": { ... }
  },
  "en": { ... mirror structure with English values ... }
}
```

## Step 2 — Recon: map the ENTIRE form first

```bash
agent-browser open <application_url> --headed
agent-browser snapshot                 # accessibility tree with refs (e1, e2, ...)
```

From the snapshot, catalogue every field: its `ref`, visible label, required (`*`),
and type (text / textarea / native-select / custom-combobox / radio / checkbox /
file / date). **Harvest dropdown options now**, so the later fill needs no extra
look-up:

- **Native `<select>`**: read options straight from the DOM in one call:
  ```bash
  agent-browser eval "[...document.querySelectorAll('select')].map(s=>({name:s.name||s.id, options:[...s.options].map(o=>o.textContent.trim())}))"
  ```
- **Custom React combobox** (options only exist once opened): open it, snapshot, note
  the option texts, close. Batch the opens so it's a few calls, not 3-per-dropdown:
  ```bash
  agent-browser click @e12 && agent-browser snapshot   # read its options
  ```

**If the form is multi-step** (Next / Continue / 下一步, or a step nav): walk each step
(`agent-browser click @<next>` → `snapshot`) until all steps are mapped. Build ONE
inventory across all steps before filling anything.

If you hit a login / SSO / CAPTCHA / OTP wall at any point, use the **Login handoff** below.

## Login handoff — let the user log in, then resume

The `--headed` window is a real browser the user can take over; the daemon keeps the
session alive, so you hand control over and resume in the same session.

1. **Stop.** Do **not** type the user's password / 2FA / OTP yourself — credentials are
   the human's to enter (and entering them is a prohibited action regardless).
2. **Tell the user**, e.g.:
   > "这一步需要登录。请在已经打开的浏览器窗口里完成登录（账号密码 / 验证码都你来操作），
   > 登录好之后跟我说一声『登录好了』，我接着填。"
3. **Wait** for their confirmation — don't re-navigate / poll / click in a loop meanwhile.
4. **On their "done"**, `agent-browser snapshot` to confirm you're past the wall (you
   see the form, not the login page). If still on login, tell them and have them retry.
5. **Resume** from where you left off.

Constraints: the user must log in **in the agent-browser window** (its own session),
and the session must stay **alive** (don't `close` it) through the handoff.

## Step 3 — Semantic match against the Excel data

- Consult `references/field_mapping.md` for the ATS-label → JSON-key map and the
  boilerplate (visa / availability / "how did you hear").
- For each field, pick the best answer from the cached `resume.json`
  (`python3 scripts/config.py cachefile`) **by meaning**, not literal label
  (e.g. "Tell us about your AI experience" → agent/LLM self-intro + relevant projects).
- For each dropdown, choose the **exact option string** from the harvested options.
- Mark as **ASK USER** (never guess): visa/eligibility, salary, availability dates,
  national ID / NRIC / passport, which resume PDF, and any free-text "why this company".
- Produce ONE fill-plan table (Field | Value | Source), flag ASK USER rows, confirm:
  > "下面是我准备填的内容，确认就开始填，要改的地方直接告诉我。"

## Step 4 — Fill in ONE shot with `agent-browser batch`

After confirmation, run a single `agent-browser batch` built from the real refs +
chosen values. Pass commands as a JSON array on stdin:

```bash
echo '[
  ["fill", "@e1", "Bo"],
  ["fill", "@e2", "Wei"],
  ["fill", "@e3", "name@example.com"],
  ["select", "@e5", "Singapore"],
  ["click", "@e8"],                       // open a custom combobox...
  ["click", "@e9"],                       // ...then click the exact option
  ["check", "@e11"],
  ["upload", "@e14", "/path/<Name>_resume.pdf"]
]' | agent-browser batch
```

Field-type → command:

| Field type | agent-browser command |
|---|---|
| text / textarea | `fill @ref "value"` (or `type` for keystroke-sensitive fields) |
| native `<select>` | `select @ref "Exact Option"` |
| custom combobox | `click @comboRef` then `click @optionRef` (the exact option) |
| radio / checkbox | `check @ref` / `uncheck @ref`, or `find role radio click --name "Yes"` |
| file upload | `upload @ref "/abs/path/file.pdf"` |
| keystroke widget | `focus @ref` then `keyboard type "..."` |

Conventions:
- `batch` defaults to **continue-on-error**, so every command's result comes back even
  if one fails — read the output to see which fields landed. (`--bail` would stop early;
  don't use it here.) **Don't loop / stall** retrying a stubborn control.
- **Multi-step**: one batch per step — fill page, `click @<next>`, snapshot, next batch.
  **Never put the final Submit click in any batch.**

## Step 4.5 — Hand stubborn fields back to the user

If a field fails in the batch and fails once more on a targeted retry, **stop fighting
it.** List those fields with the exact value that should go in and have the user fill
those few by hand. (Optionally try the Playwright CLI fallback first if it's a widget
agent-browser genuinely can't drive.)

## Step 5 — Verify once + stop before Submit

```bash
agent-browser snapshot          # or: agent-browser screenshot review.png
```

Report:
```
✅ 表单已填完，未提交。请人工检查后自行点 Submit。
   - 已填: <list>
   - 需你手填(自动填失败): <field> = <value>
   - 跳过 / 留空: <field> (<reason>)
   - Resume 已上传: <PDF path>
```

**Never click Submit.** Leave the `--headed` window open for the user to review and
submit. (`agent-browser close` only when they're done.)

## Step 6 (optional) — Log the application

Only on explicit user request after they confirm they submitted: append a row to the
`跳转投递记录` sheet in the Excel (company, role, date, JD URL, status). Don't pre-log
a submission you didn't witness.

---

## Things to watch for

- **Forms that auto-populate from the uploaded resume** (Greenhouse, Workday): `upload`
  the resume during recon, `snapshot` again, then fill only the gaps + fix misparses.
- **Multi-step forms**: recon must traverse all steps before filling.
- **Login / SSO / CAPTCHA / OTP**: use the **Login handoff** — let the user log in in
  the `--headed` window, wait for "done", verify, resume.
- **OS file pickers**: don't try to drive the native dialog; use `upload @ref <path>`.
- **Free-text Q&A** ("Why this company?", "Tell us about your AI experience"): never
  boilerplate — draft fresh from the JD + recent projects, or hand a draft to the user.

## Anti-patterns

- ❌ Using the Playwright MCP (`browser_*`). Use the `agent-browser` CLI; Playwright CLI
  only as a last-resort fallback.
- ❌ Filling field-by-field across many calls. Harvest options in recon, fill with one
  `agent-browser batch`.
- ❌ Re-snapshotting after every field. Verify once at the end.
- ❌ Looping / stalling on one stubborn control. Retry once, then hand it to the user.
- ❌ Filling before you've surveyed the whole (multi-step) form.
- ❌ Hardcoding the Excel path, or re-asking for it (it's saved via `scripts/config.py`).
- ❌ Hardcoding a fixed selector template instead of building from this form's recon.
- ❌ Auto-clicking Submit "because the user said fill it".
- ❌ Guessing visa / salary / availability / ID number / which resume without asking.
- ❌ Pasting a full ID / passport / family phone unless the form requires it AND the
  user okays it for this submission.
- ❌ Filling from stale data — always re-dump the resume cache first.
