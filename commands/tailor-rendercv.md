---
description: Tailor your master RenderCV YAML to a job description, render a styled PDF with RenderCV, generate a matching ATS/Workday DOCX, score both against ATS + HR rubrics, and update the tracker.
---

# Tailor Resume → RenderCV YAML + PDF (+ ATS DOCX)

Tailor a resume by editing your **master RenderCV YAML**, render it to a polished PDF with
RenderCV, and emit a matching **ATS/Workday DOCX** from the same YAML — so the human-facing
PDF and the ATS upload never drift. resume-builder does the tailoring + scoring; RenderCV
does the rendering. Target: ATS 75–85% + HR 70%+ with AUTHENTIC content.

## Job Description
$ARGUMENTS

## Instructions

You are an expert ATS optimization specialist. Tailor the master RenderCV YAML — never the
DOCX generator's markdown format. Execute the phases below.

---

## PHASE 0: CONFIG + SCORER PRE-FLIGHT

Read `config.json` and pull:
- `master_yaml_path`  — the master RenderCV `.yaml` (source of truth). **If missing, stop** and
  tell the user to set it to their RenderCV resume YAML.
- `rendercv_command`  — how to invoke RenderCV (default `./.venv/bin/rendercv`).
- `python_command`    — a Python with PyYAML + python-docx + scorer deps (default `python3`;
  use an absolute path if bare `python` is version-pinned in this repo).
- `output_base_dir`   — usually `applications`.

Check the scorer server: `curl -s http://localhost:8100/health`
- Healthy → proceed. Not running → start it in a background shell:
  `{python_command} scorer_server.py --port 8100` (retry `/health` up to 30s).
- Fallback: score via CLI (`{python_command} ats_scorer.py --score ... --json`).

---

## PHASE 1: SETUP + READ MASTER

- Extract the **Company** and **Job Title** from the JD.
- Create the output folder: `{output_base_dir}/{Company} - {Job Title}/`
- Save the JD as `{folder}/job_description.txt`.
- Read the master RenderCV YAML. Note the EXACT `name`, per-role `position` / `company` /
  dates / `location`, `education`, and the whole `design:` block — these are canonical.

---

## PHASE 2: TAILOR THE YAML

Copy the master YAML to `{folder}/{Name}_{Company}.yaml`, then edit **ONLY** these:

1. **`professional_summary`** (or `summary`) — 3–4 sentences, lead with results, weave in 3–5
   exact JD terms.
2. **`core_competencies`** — regroup the `label`/`details` entries to mirror the JD's stack
   (e.g. group by Backend & APIs / Data / Cloud / Frontend / Security & Quality). Use the JD's
   exact tool names. This is the primary keyword location.
3. **experience `highlights`** — reframe existing bullets with JD language; keep the
   `**Lead-in:** …` bold prefixes. Recency-weighted: current role 4–6 bullets, recent 3–4,
   older 1–2. Drop the weakest bullets on old roles to keep it to ~2 pages.

**Do NOT touch:** `name`, any `position` / `company` / `location` / dates, `education`, or the
`design:` block. Never invent experience. Never add a tool that is not in `validated_tools`
(config.json) unless the user has explicitly confirmed it.

Then set the tailored YAML's render settings so outputs land in the folder without clobbering
the master:

```yaml
rendercv_settings:
  render_command:
    output_folder_name: {folder}/_render
    pdf_path: {folder}/{Name}_Resume_{Company}.pdf
    dont_generate_markdown: false   # needed for scoring
    dont_generate_html: true
    dont_generate_png: true
```

---

## PHASE 3: RENDER THE PDF

```
{rendercv_command} render "{folder}/{Name}_{Company}.yaml"
```

Produces `{folder}/{Name}_Resume_{Company}.pdf` and a Markdown file under `{folder}/_render/`
(named `<cv.name>_CV.md`) used for scoring. If it fails on a path with spaces, render to a
no-space folder and copy the PDF into `{folder}/`.

---

## PHASE 4: GENERATE THE ATS DOCX (same YAML → DOCX)

```
{python_command} ${CLAUDE_PLUGIN_ROOT}/rendercv_to_docx.py "{folder}/{Name}_{Company}.yaml" "{folder}/{Name}_Resume_{Company}.docx"
```

This maps the tailored YAML to an ATS/Workday DOCX (handles international contacts, strips
lead-in markdown, flattens competencies into keywords). Single source = the YAML.

---

## PHASE 5: SCORE + ITERATE (max 2 rounds)

Score the rendered Markdown (`{folder}/_render/<cv.name>_CV.md`) against the JD:
```
curl -s -X POST http://localhost:8100/score/both -H "Content-Type: application/json" \
  -d "{\"resume_path\": \"{folder}/_render/<cv.name>_CV.md\", \"jd_path\": \"{folder}/job_description.txt\"}"
```
(Fallback: CLI scorers.) Also score the master's rendered Markdown once for the base comparison.

```
IF ATS < 75:  add JD keywords to core_competencies; reframe 1–2 bullets → re-render (Phase 3) → re-score
IF ATS ≥ 75 AND HR < 70:  strengthen bullet impact/metrics → re-render → re-score
IF ATS ≥ 75 AND HR ≥ 70:  PASS
```
Each iteration edits the YAML, re-renders, re-scores. After a passing (or 2nd) round, regenerate
the DOCX (Phase 4) so it matches the final YAML.

---

## PHASE 6: TRACKER + REPORT

Update the tracker:
```
{python_command} -c "from tracker_utils import add_application; add_application(company='{Company}', job_title='{Job Title}', resume_file='{Name}_Resume_{Company}.docx', cover_letter_file='', jd_file='job_description.txt', ats_score={final_ats}, hr_score={final_hr}, status='Applied')"
```

Report:
```
================================================================
  RESUME TAILOR (RenderCV) — {Company}
================================================================
  POSITION: {Job Title}
                 |  BASE  |  TAILORED  |  Δ
  ATS            | {b}%   |  {t}%      | +{d}
  HR             | {b}%   |  {t}%      | +{d}   → {recommendation}
----------------------------------------------------------------
  OUTPUT (in applications/{Company} - {Job Title}/):
    {Name}_{Company}.yaml         tailored RenderCV source
    {Name}_Resume_{Company}.pdf   styled PDF (RenderCV)
    {Name}_Resume_{Company}.docx  ATS / Workday DOCX
================================================================
```

## AUTHENTICITY (NON-NEGOTIABLE)
- Titles, companies, dates, education, and the `design:` block are copied verbatim from master.
- Only reframe existing achievements — never fabricate experience or add unconfirmed tools.
- Keep any single keyword to 1–2 appearances; authentic 78% beats stuffed 90%.
