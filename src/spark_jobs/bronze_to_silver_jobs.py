"""Silver Layer processing pipeline.

Performs data cleansing, field standardization, role classification, salary
normalization, tech skill extraction, and ACID deduplication (MERGE INTO)
for the Silver Medallion layer:
  - silver/delta_jobs
  - silver/delta_job_skills
"""

from __future__ import annotations

import ast
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from src.config import settings
from src.spark_jobs.skill_extractor import extract_skills_for_record

logger = logging.getLogger(__name__)

# Currency conversion rate to IDR
USD_TO_IDR_RATE = 16000.0


def normalize_employment_type(val: str | None) -> str:
    """Standardize employment type into predefined Kimball categories."""
    if not val:
        return "Full-Time"
    text = str(val).strip().lower()
    if "intern" in text or "magang" in text:
        return "Internship"
    if "part" in text or "paruh waktu" in text:
        return "Part-Time"
    if "contract" in text or "kontrak" in text or "freelance" in text or "project" in text:
        return "Contract"
    if "full" in text or "penuh waktu" in text or "permanent" in text or "tetap" in text:
        return "Full-Time"
    return "Other"


def normalize_experience_level(val: str | None) -> str:
    """Standardize experience requirements."""
    if not val:
        return "Unspecified"
    text = str(val).strip().lower()
    if any(k in text for k in ["fresh", "entry", "intern", "lulusan baru", "0-1", "0 yr"]):
        return "Fresh Graduate / Entry"
    if any(k in text for k in ["junior", "1-2", "1-3", "1 yr", "2 yr"]):
        return "Junior (1-3 yrs)"
    if any(k in text for k in ["mid", "3-5", "2-4", "3 yr", "4 yr"]):
        return "Mid-Senior (3-5 yrs)"
    if any(
        k in text
        for k in ["senior", "lead", "principal", "manager", "head", "5+", "5-", "6+", "7+"]
    ):
        return "Senior (5+ yrs)"
    return "Unspecified"


def normalize_work_policy(val: str | None) -> str:
    """Standardize work policy to Remote, Hybrid, or WFO."""
    if not val:
        return "WFO"
    text = str(val).strip().lower()
    if "remote" in text or "wfh" in text or "work from home" in text:
        return "Remote"
    if "hybrid" in text or "fleksibel" in text:
        return "Hybrid"
    if "onsite" in text or "on-site" in text or "wfo" in text or "office" in text:
        return "WFO"
    return "WFO"


ROLE_PATTERNS: list[tuple[str, str]] = [
    (
        "Data Engineer",
        r"\b(data\s+engineer|etl|pipeline|big\s*data|analytics\s+engineer|dwh|lakehouse)\b",
    ),
    (
        "Data Analyst / Scientist",
        r"\b(data\s+analyst|data\s+analytics|bi\s+analyst|business\s+intelligence|statistician)\b",
    ),
    (
        "AI / ML Engineer",
        r"\b(data\s+scientist|machine\s+learning|ai\s+engineer|ml\s+engineer|deep\s+learning|mlops|nlp)\b",
    ),
    (
        "Backend Engineer",
        r"\b(backend|back-end|golang|java\b|node|python\s+dev|api\s+dev|software\s+engineer.*backend)\b",
    ),
    (
        "Frontend / Fullstack",
        r"\b(frontend|front-end|react|vue|angular|fullstack|full-stack|web\s+developer)\b",
    ),
    (
        "DevOps / Cloud",
        r"\b(devops|sre|site\s+reliability|cloud\s+engineer|infrastructure|platform\s+engineer|sysadmin)\b",
    ),
    (
        "Mobile Developer",
        r"\b(android|ios|flutter|react\s+native|mobile\s+developer|mobile\s+engineer)\b",
    ),
    (
        "QA / Security",
        r"\b(qa|quality\s+assurance|tester|test\s+engineer|security|cybersecurity)\b",
    ),
]


def classify_role_category(job_title: str | None) -> str:
    """Classify tech job title into standard IT role categories."""
    if not job_title:
        return "Other IT"
    t = str(job_title).lower()

    for role_name, pattern in ROLE_PATTERNS:
        if re.search(pattern, t):
            return role_name

    return "Other IT"


def normalize_location(raw_loc: Any) -> str:
    """Normalize raw location string or dictionary into 'Negara, Kota' template (e.g. 'Indonesia, Jakarta')."""
    if not raw_loc:
        return "Indonesia, Jakarta"
    s = str(raw_loc).strip()
    if s.lower() in ("none", "null", "nan", ""):
        return "Indonesia, Jakarta"

    # 1. If it's a dict or stringified dict from Glints
    if s.startswith("{") or "typename" in s.lower():
        city = None
        country = "Indonesia"
        try:
            d = ast.literal_eval(s) if s.startswith("{") else None
            if isinstance(d, dict):
                parents = d.get("parents") or []
                for p in parents:
                    if isinstance(p, dict):
                        lvl = str(p.get("administrativeLevelName", "")).lower()
                        p_name = p.get("name") or p.get("formattedName")
                        if lvl in ("city", "kabupaten") and p_name:
                            city = p_name
                            break
                        if str(p.get("level")) == "3" and p_name:
                            city = p_name
                            break
                if not city:
                    city = d.get("name") or d.get("formattedName")
        except Exception:
            m_city = re.search(r"'(?:name|formattedName)':\s*'([^']+)'", s)
            if m_city:
                city = m_city.group(1)

        city = _clean_city_name(city)
        return f"{country}, {city}"

    # 2. String formats like 'Jakarta Selatan, Jakarta Raya', 'Bandung, Jawa Barat', 'Indonesia, Jakarta'
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) >= 2:
        if parts[0].lower() == "indonesia":
            c = _clean_city_name(parts[1])
        else:
            c = _clean_city_name(parts[0])
        return f"Indonesia, {c}"
    elif len(parts) == 1:
        c = _clean_city_name(parts[0])
        return f"Indonesia, {c}"

    return "Indonesia, Jakarta"


def _clean_city_name(c: str | None) -> str:
    """Normalize Indonesian city name."""
    if not c:
        return "Jakarta"
    name = str(c).strip()
    if name.lower() in ("indonesia", "id", "country", "none", "null", ""):
        return "Jakarta"
    if re.search(r"\bjakarta\b", name, re.IGNORECASE):
        return "Jakarta"
    name = re.sub(r"^(Kabupaten|Kab\.|Kota|Kapanewon)\s+", "", name, flags=re.IGNORECASE).strip()
    return name if name and name.lower() != "indonesia" else "Jakarta"


def normalize_salary(
    min_sal: float | None,
    max_sal: float | None,
    currency: str | None,
) -> tuple[float | None, float | None]:
    """Convert salary figures to IDR monthly and validate range."""
    def _is_valid_sal(val: Any) -> bool:
        if val is None:
            return False
        try:
            f = float(val)
            return not math.isnan(f) and not math.isinf(f) and f > 0
        except (ValueError, TypeError):
            return False

    v_min = float(min_sal) if _is_valid_sal(min_sal) else None
    v_max = float(max_sal) if _is_valid_sal(max_sal) else None

    curr = (currency or "IDR").upper()
    rate = USD_TO_IDR_RATE if curr == "USD" else 1.0

    sal_min = v_min * rate if v_min is not None else None
    sal_max = v_max * rate if v_max is not None else None

    # Ensure min <= max if both exist
    if sal_min is not None and sal_max is not None and sal_min > sal_max:
        sal_min, sal_max = sal_max, sal_min

    return sal_min, sal_max


def clean_and_transform_job(record: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Normalize a raw job record and extract its skills."""
    job_id = str(record["job_id"])
    title = str(record.get("job_title", "Software Engineer"))
    description = str(record.get("job_description", ""))
    currency = str(record.get("currency", "IDR"))

    sal_min, sal_max = normalize_salary(
        record.get("salary_min"),
        record.get("salary_max"),
        currency,
    )

    clean_job = {
        "job_id": job_id,
        "source": str(record.get("source", "unknown")),
        "job_title": title,
        "role_category": classify_role_category(title),
        "company_name": str(record.get("company_name", "Confidential Company")),
        "company_industry": str(record.get("company_industry"))
        if record.get("company_industry")
        else None,
        "company_location": normalize_location(record.get("company_location")),
        "employment_type": normalize_employment_type(record.get("employment_type")),
        "work_policy": normalize_work_policy(record.get("work_policy")),
        "experience_level": normalize_experience_level(record.get("experience_level")),
        "salary_min_idr": sal_min,
        "salary_max_idr": sal_max,
        "job_description": description,
        "job_url": str(record.get("job_url", "")),
        "posted_at": str(record.get("posted_at")) if record.get("posted_at") else None,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    skills = extract_skills_for_record(job_id, title, description)
    return clean_job, skills


def run_silver_pipeline(
    base_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Execute Silver Layer transformation: Bronze -> Cleansing -> Silver Delta/Parquet."""
    data_dir = Path(base_dir) if base_dir else settings.local_data_dir
    bronze_jobs_dir = data_dir / "bronze" / "jobs"
    silver_dir = data_dir / "silver"
    silver_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "jobs_processed": 0,
        "skills_extracted": 0,
        "silver_jobs_file": None,
        "silver_skills_file": None,
    }

    if not bronze_jobs_dir.exists():
        logger.warning("Bronze jobs directory does not exist: %s", bronze_jobs_dir)
        return summary

    parquet_files = list(bronze_jobs_dir.glob("**/*.parquet"))
    if not parquet_files:
        logger.info("No Bronze parquet files found to process.")
        return summary

    logger.info("Reading %d Bronze Parquet files via DuckDB...", len(parquet_files))
    con = duckdb.connect(":memory:")
    query = f"SELECT * FROM read_parquet('{bronze_jobs_dir}/**/*.parquet')"
    bronze_df = con.execute(query).df()
    con.close()

    if bronze_df.empty:
        logger.info("Bronze DataFrame is empty.")
        return summary

    # Transform and extract skills
    clean_jobs_map: dict[str, dict[str, Any]] = {}
    all_skills: list[dict[str, Any]] = []

    for _, row in bronze_df.iterrows():
        record = row.to_dict()
        clean_job, skills = clean_and_transform_job(record)
        # Deduplication by job_id (MERGE / Upsert behavior)
        clean_jobs_map[clean_job["job_id"]] = clean_job
        all_skills.extend(skills)

    unique_jobs = list(clean_jobs_map.values())
    summary["jobs_processed"] = len(unique_jobs)
    summary["skills_extracted"] = len(all_skills)

    # Explicit PyArrow schemas to guarantee valid Parquet even with empty results
    jobs_schema = pa.schema(
        [
            ("job_id", pa.string()),
            ("source", pa.string()),
            ("job_title", pa.string()),
            ("role_category", pa.string()),
            ("company_name", pa.string()),
            ("company_industry", pa.string()),
            ("company_location", pa.string()),
            ("employment_type", pa.string()),
            ("work_policy", pa.string()),
            ("experience_level", pa.string()),
            ("salary_min_idr", pa.float64()),
            ("salary_max_idr", pa.float64()),
            ("job_description", pa.string()),
            ("job_url", pa.string()),
            ("posted_at", pa.string()),
            ("updated_at", pa.string()),
        ]
    )

    skills_schema = pa.schema(
        [
            ("job_id", pa.string()),
            ("skill_id", pa.string()),
            ("skill_name", pa.string()),
            ("skill_category", pa.string()),
        ]
    )

    # Write Silver Jobs (delta_jobs)
    jobs_out_dir = silver_dir / "delta_jobs"
    jobs_out_dir.mkdir(parents=True, exist_ok=True)
    jobs_parquet = jobs_out_dir / "part-0000.parquet"
    table_jobs = pa.Table.from_pylist(unique_jobs, schema=jobs_schema)
    pq.write_table(table_jobs, jobs_parquet, compression="SNAPPY")
    summary["silver_jobs_file"] = str(jobs_parquet)

    # Write Silver Skills (delta_job_skills)
    skills_out_dir = silver_dir / "delta_job_skills"
    skills_out_dir.mkdir(parents=True, exist_ok=True)
    skills_parquet = skills_out_dir / "part-0000.parquet"
    table_skills = pa.Table.from_pylist(all_skills, schema=skills_schema)
    pq.write_table(table_skills, skills_parquet, compression="SNAPPY")
    summary["silver_skills_file"] = str(skills_parquet)

    logger.info(
        "=== Silver Processing Complete: %d jobs saved, %d skill relationships extracted ===",
        len(unique_jobs),
        len(all_skills),
    )
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_silver_pipeline()
