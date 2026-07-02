#!/usr/bin/env python3
"""
Convert a tailored RenderCV YAML into an ATS / Workday-compatible DOCX.

The RenderCV YAML is the single source of truth: rendercv renders it to a styled
PDF, and this script renders the SAME content to a DOCX via docx_generator, so an
ATS upload and a human-facing PDF never drift.

Handles international contacts (e.g. Brazilian phone / "City, Country") that the
markdown-based parser drops, strips bold/italic lead-in markdown from bullets, and
flattens grouped competencies into ATS keywords.

Usage:
    python rendercv_to_docx.py <input.yaml> <output.docx>

Run with a Python that has PyYAML + python-docx (docx_generator's deps).
"""
import re
import sys

import yaml

from docx_generator import create_ats_resume

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_date(d) -> str:
    """RenderCV dates (YYYY-MM, YYYY, 'present') -> 'Mon YYYY' / 'Present'."""
    if d is None:
        return ""
    d = str(d).strip()
    if d.lower() in ("present", ""):
        return "Present" if d else ""
    m = re.match(r"(\d{4})-(\d{1,2})", d)
    if m:
        return f"{_MONTHS[int(m.group(2)) - 1]} {m.group(1)}"
    m = re.match(r"(\d{4})", d)
    return m.group(1) if m else d


def _strip_md(s: str) -> str:
    """Drop **bold** / *italic* markers, keep the text."""
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\*(.+?)\*", r"\1", s)
    return s.strip()


def _dates(entry) -> str:
    lo, hi = _fmt_date(entry.get("start_date")), _fmt_date(entry.get("end_date"))
    return f"{lo} – {hi}".strip(" –") if (lo or hi) else str(entry.get("date", "")).strip()


def _first_section(sections, *keys):
    for k in keys:
        if k in sections:
            return sections[k]
    return None


def convert(yaml_path: str, docx_path: str) -> None:
    with open(yaml_path, encoding="utf-8") as f:
        cv = yaml.safe_load(f)["cv"]

    # --- Contact (robust to international formats) ---
    phone = re.sub(r"^tel:", "", str(cv.get("phone", ""))).replace("-", " ").strip()
    loc = str(cv.get("location", "")).strip()
    city, state = (loc.rsplit(",", 1) + [""])[:2] if "," in loc else (loc, "")
    socials = {s.get("network", "").lower(): s.get("username", "")
               for s in cv.get("social_networks", [])}
    links = []
    if socials.get("linkedin"):
        links.append(f"linkedin.com/in/{socials['linkedin']}")
    if socials.get("github"):
        links.append(f"github.com/{socials['github']}")
    contact = {"city": city.strip(), "state": state.strip(), "zip": "",
               "phone": phone, "email": cv.get("email", ""),
               "linkedin": "  |  ".join(links)}

    sections = cv.get("sections", {}) or {}

    # --- Summary ---
    summ = _first_section(sections, "professional_summary", "summary")
    summary = " ".join(summ) if isinstance(summ, list) else (summ or "")

    # --- Core competencies (flatten grouped label/details -> deduped keywords) ---
    comps, seen = [], set()
    for item in (_first_section(sections, "core_competencies", "skills", "competencies") or []):
        vals = ([c.strip() for c in item["details"].split(",")]
                if isinstance(item, dict) and "details" in item
                else [str(item).strip()])
        for c in vals:
            if c and c.lower() not in seen:
                seen.add(c.lower())
                comps.append(c)

    # --- Experience ---
    experience = []
    for job in (_first_section(sections, "professional_experience", "experience") or []):
        experience.append({
            "title": job.get("position", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "dates": _dates(job),
            "bullets": [_strip_md(h) for h in job.get("highlights", []) if str(h).strip()],
        })

    # --- Education ---
    education = []
    for e in (sections.get("education") or []):
        deg = e.get("degree", "")
        if e.get("area"):
            deg = f"{deg} in {e['area']}".strip() if deg else e["area"]
        education.append({
            "degree": deg,
            "school": e.get("institution", ""),
            "location": e.get("location", ""),
            "dates": _dates(e),
        })

    create_ats_resume(
        output_path=docx_path, name=cv.get("name", ""), contact_info=contact,
        summary=summary, core_competencies=comps, experience=experience,
        education=education, certifications=[],
    )
    print(f"DOCX written: {docx_path}")
    print(f"  jobs={len(experience)}  education={len(education)}  competencies={len(comps)}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Usage: python rendercv_to_docx.py <input.yaml> <output.docx>")
    convert(sys.argv[1], sys.argv[2])
