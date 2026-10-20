"""Unit tests for technical skill extraction logic and regex boundaries."""

from __future__ import annotations

from src.spark_jobs.skill_extractor import (
    extract_skills_for_record,
    extract_skills_from_text,
    generate_skill_id,
)


def test_skill_id_deterministic() -> None:
    """Test that skill_id is deterministic and lowercase-normalized."""
    id1 = generate_skill_id("Python")
    id2 = generate_skill_id("python")
    id3 = generate_skill_id(" Python ")
    assert id1 == id2 == id3
    assert len(id1) == 12


def test_extract_skills_basic_matching() -> None:
    """Test standard tech skills are detected correctly."""
    text = (
        "We are looking for a Senior Data Engineer skilled in Python, PySpark, "
        "SQL, dbt, and Apache Airflow. Experience with Docker and Kubernetes is a plus."
    )
    skills = extract_skills_from_text(text)
    skill_names = {s["skill_name"] for s in skills}

    assert "Python" in skill_names
    assert "PySpark" in skill_names
    assert "SQL" in skill_names
    assert "dbt" in skill_names
    assert "Airflow" in skill_names
    assert "Docker" in skill_names
    assert "Kubernetes" in skill_names


def test_extract_skills_false_positive_prevention() -> None:
    """Ensure common English words never trigger false positive skill matches."""
    # 'Golang' vs 'good' / 'going' / 'go'
    text_golang_false = "Must have good communication skills and be going to the office."
    skills_golang_false = extract_skills_from_text(text_golang_false)
    assert not any(s["skill_name"] == "Golang" for s in skills_golang_false)

    # 'Java' vs 'JavaScript'
    text_js_only = "Looking for a Frontend Developer experienced in JavaScript and React."
    skills_js = extract_skills_from_text(text_js_only)
    assert any(s["skill_name"] == "JavaScript" for s in skills_js)
    assert not any(s["skill_name"] == "Java" for s in skills_js)

    # 'C' vs 'CEO' / 'CV'
    text_c_false = "Please send your CV directly to the CEO."
    skills_c = extract_skills_from_text(text_c_false)
    assert not any(s["skill_name"] == "C" for s in skills_c)


def test_special_characters_programming_languages() -> None:
    """Test special character languages like C++ and C#."""
    text_cpp_cs = "Candidates must have experience with C++ or C# and .NET frameworks."
    skills = extract_skills_from_text(text_cpp_cs)
    skill_names = {s["skill_name"] for s in skills}
    assert "C++" in skill_names
    assert "C#" in skill_names


def test_extract_skills_for_record() -> None:
    """Test record-level extraction associating job_id with extracted skills."""
    rows = extract_skills_for_record(
        job_id="job-999",
        job_title="Data Engineer",
        job_description="Proficiency in PySpark, Kafka, and PostgreSQL required.",
    )
    assert len(rows) >= 3
    for r in rows:
        assert r["job_id"] == "job-999"
        assert "skill_id" in r
        assert "skill_name" in r
        assert "skill_category" in r
