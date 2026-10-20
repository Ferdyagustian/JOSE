"""Technical skill extraction engine using strict word boundary Regex patterns.

Extracts technology skills from job titles and descriptions while preventing
false positive matches (e.g. 'go' in 'good', 'java' in 'javascript', 'c' in 'ceo').
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from src.config import TECH_SKILLS_CATALOG, SkillDefinition


def generate_skill_id(skill_name: str) -> str:
    """Generate deterministic 12-char surrogate ID for a skill name."""
    clean = skill_name.strip().lower()
    return hashlib.md5(clean.encode("utf-8")).hexdigest()[:12]


# Pre-compile regex patterns at module load for high throughput
COMPILED_SKILL_PATTERNS: list[tuple[SkillDefinition, str, re.Pattern]] = [
    (
        skill_def,
        generate_skill_id(skill_def.name),
        re.compile(skill_def.regex_pattern, re.IGNORECASE),
    )
    for skill_def in TECH_SKILLS_CATALOG.values()
]


def extract_skills_from_text(text: str) -> list[dict[str, str]]:
    """Extract all matched technical skills from arbitrary text.

    Returns a list of dicts with keys: 'skill_id', 'skill_name', 'skill_category'.
    """
    if not text:
        return []

    matched: list[dict[str, str]] = []
    seen_skills: set[str] = set()

    for skill_def, skill_id, pattern in COMPILED_SKILL_PATTERNS:
        if pattern.search(text) and skill_def.name not in seen_skills:
            seen_skills.add(skill_def.name)
            matched.append(
                {
                    "skill_id": skill_id,
                    "skill_name": skill_def.name,
                    "skill_category": skill_def.category,
                }
            )

    return matched


def extract_skills_for_record(
    job_id: str,
    job_title: str,
    job_description: str,
) -> list[dict[str, Any]]:
    """Extract skills for a specific job posting and associate with job_id.

    Returns rows formatted for the silver delta_job_skills table:
    [{"job_id": ..., "skill_id": ..., "skill_name": ..., "skill_category": ...}]
    """
    combined_text = f"{job_title or ''} {job_description or ''}"
    skills = extract_skills_from_text(combined_text)

    records: list[dict[str, Any]] = []
    for s in skills:
        records.append(
            {
                "job_id": str(job_id),
                "skill_id": s["skill_id"],
                "skill_name": s["skill_name"],
                "skill_category": s["skill_category"],
            }
        )
    return records
