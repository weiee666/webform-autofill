# Field Mapping: ATS form fields → user's resume JSON

Use this as a dictionary when matching form fields you see on a careers / ATS page to entries from `cache/resume.json`. Most modern ATS forms (Greenhouse, Lever, Workday, Breezy, Workable, Shopee careers, Bytedance careers, etc.) use these field names with small variations.

When a form label doesn't match anything here, infer from context, fall back on common sense, and surface the field to the user when ambiguous.

## Personal info

> Values come from `cache/resume.json` at runtime — this table maps form labels to
> JSON keys, it does **not** hardcode personal data.

| Form field (any of) | Source in resume.json | Notes |
|---|---|---|
| First Name | given-name part of `基本信息.姓名` | romanise for English ATS |
| Last Name / Family Name / Surname | family-name part of `基本信息.姓名` |  |
| Full Name | `en.基本信息.姓名` for English ATS; `zh.基本信息.姓名` for 中文表单 |  |
| Preferred Name / English Name | romanised given + family name |  |
| Chinese Name | `zh.基本信息.姓名` |  |
| Email | prefer `en.基本信息.常用邮箱2` (school email) for tech / Singapore roles; `基本信息.常用邮箱` if the form wants a personal email | a school email signals "current student" — usually the right call. Confirm if both present. |
| Mobile / Contact Number | `基本信息.手机号1` (current SG SIM); fallback `手机号2` (CN number) only if explicitly asked |  |
| Country Code | `+65` Singapore by default for current job hunt |  |
| Current Location / City | `Singapore` |  |
| Nationality / Citizenship | `China` |  |
| Gender | `基本信息.性别` (Male / 男) |  |
| Date of Birth | derive from `基本信息.身份证号码` — **do not hardcode** |  |
| NRIC / Passport last 4 / National ID | only fill if explicitly asked; pull from `基本信息.身份证号码`. **Never paste the full ID unless it is a required field.** |  |

## Education

`zh.教育经历` / `en.教育经历` is a list. Education 1 = current NTU master's, Education 2 = bachelor at Wuhan University of Technology (or whichever is recorded).

| Form field | JSON key |
|---|---|
| Education Level | `最高学历` (Master / Bachelor — translate to ATS dropdown values) |
| School / University | `学历N-学校名称` |
| Course of Study / Major | `学历N-专业` |
| Degree / Qualification | `学历N-学位` (e.g., 硕士 / Master of Science) |
| Course Period — Start | `学历N-入学时间` |
| Course Period — End | `学历N-毕业时间` |
| Degree Classification | usually not in JSON; default Pass / Honours-equivalent if available, else leave for user |
| CGPA | usually blank — surface to user if required (NTU GPA likely on transcript) |
| Transcript file | path on disk — ask user |

## Experience (Work + Internship)

Two parallel arrays: `工作经历` and `实习经历`. For ATS that asks "Experience", include both, ordered **most recent first**:

1. **Tenth Global** — Agent Developer Intern — Apr 2026 – Present (Singapore)
2. **Hankou Bank / Commercial Bank** — Product Manager — Jul 2021 – May 2024 (Wuhan)
3. GF Securities (实习经历2) — 2020 — Account Manager
4. Ping An Financial Leasing (实习经历1) — 2019 — Account Manager

Field mapping:

| Form field | JSON key |
|---|---|
| Company | `工作单位` |
| Designation / Job Title / Role | `工作岗位` |
| Work Start | `开始时间` |
| Work End | `结束时间` (use "Present" / "至今" for ongoing) |
| Department | `部门名称` |
| Description | `工作描述` |

## Skills

`技能栈` (dict) — pick the 5–8 most relevant for the role.

For LLM / Agent / Backend roles, prefer: Python, MySQL, Flask, Anthropic SDK, prompt engineering, LoRA / fine-tuning, SQL, agent design.

For Data Science / Analyst roles: Python, SQL, Pandas, Tableau, EDA, scikit-learn, AUPRC / class-imbalance evaluation.

For PM / business roles: stakeholder management, PRD writing, MySQL, API design, prompt engineering, cross-team coordination.

## Links

`链接` dict has: 领英 / github / tableaupublic / 个人网站 / 个人博客 / 小红书.

| Form field | JSON key |
|---|---|
| LinkedIn URL | `领英` (already full URL) |
| GitHub URL | `github` |
| Portfolio / Website | `个人网站` |
| Tableau Public | `tableaupublic` |
| Other URL | use 个人博客 |

## "Other Information" boilerplate answers

| Form field | Answer |
|---|---|
| Visa sponsorship / immigration support | **"Yes — I am currently on a Student Pass at NTU Singapore and will require employer-sponsored EP / S-Pass for full-time employment in Singapore."** For internships during studies, answer "No — I can work in Singapore on my Student Pass during the internship period." |
| Availability period (intern) | Match the JD's window — typically "May 2026 onwards" for Summer; "From now / immediate" for off-cycle. **Always confirm with user.** |
| How did you hear about this role? | LinkedIn / company website / referral — surface to user if uncertain. |
| Channel | LinkedIn unless user specifies otherwise |
| Notice period | "Available immediately" (currently a student) |
| Expected Salary | **Leave blank** unless user provides; this is a negotiation trap. |

## File uploads

- **Resume PDF**: pull from the most recent `已投递公司/<NN_company_role>/<Name>_resume.pdf`. If a role-specific resume hasn't been built yet, **ask user before falling back** to a generic one.
- **Cover letter**: only if explicitly requested and one exists.
- **Transcript**: ask user — these are typically stored separately and may need to be fetched from NTU portal.
- **Supporting documents**: ask user.

## Self-introduction / "Why this company?" boxes

- For "Tell us about yourself": use `en.自我介绍._value` if present, else compose from summary of latest resume.
- For "Why this company?" / "Why this role?": **always draft fresh** with the JD context — don't reuse boilerplate.

## Dropdowns

Most ATS dropdowns are strings — match by case-insensitive substring against the JSON value. For Education Level dropdowns, common ATS values:
- "Master's degree" / "Master" / "Postgraduate" → 硕士
- "Bachelor's degree" / "Bachelor" / "Undergraduate" → 本科

## Country / region

Default `Singapore` for current location. For nationality, `China` / `Chinese`.
