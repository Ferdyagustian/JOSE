"""Unit tests for central configuration and skill catalog."""

import re

from src.config import MONITORED_YOUTUBE_SKILLS, TECH_SKILLS_CATALOG, settings


def test_settings_initialization() -> None:
    """Test that settings load default values properly."""
    assert settings.environment == "development"
    assert settings.bronze_container == "bronze"
    assert settings.silver_container == "silver"
    assert settings.gold_container == "gold"
    assert not settings.is_production


def test_tech_skills_catalog_integrity() -> None:
    """Test that the master skills catalog contains expected skills with valid regex."""
    assert len(TECH_SKILLS_CATALOG) >= 35

    # Check key foundational skills exist
    assert "Python" in TECH_SKILLS_CATALOG
    assert "SQL" in TECH_SKILLS_CATALOG
    assert "PySpark" in TECH_SKILLS_CATALOG
    assert "dbt" in TECH_SKILLS_CATALOG
    assert "Docker" in TECH_SKILLS_CATALOG

    # Verify that all regex patterns compile without error
    for skill_name, skill_def in TECH_SKILLS_CATALOG.items():
        assert skill_def.name == skill_name
        assert skill_def.category in [
            "Programming Language",
            "Data Engineering",
            "Cloud & DevOps",
            "Database",
            "Framework",
        ]
        # Regex must compile cleanly
        compiled_regex = re.compile(skill_def.regex_pattern, re.IGNORECASE)
        assert compiled_regex is not None


def test_monitored_youtube_skills() -> None:
    """Test that all monitored YouTube skills are present in the master catalog."""
    assert len(MONITORED_YOUTUBE_SKILLS) > 0
    for skill in MONITORED_YOUTUBE_SKILLS:
        assert skill in TECH_SKILLS_CATALOG


def test_regex_word_boundaries_edge_cases() -> None:
    """Test that regex patterns prevent false positive matches."""
    # Test 'Golang' regex does not match 'good' or 'going'
    golang_pattern = re.compile(TECH_SKILLS_CATALOG["Golang"].regex_pattern, re.IGNORECASE)
    assert golang_pattern.search("We need a senior Golang developer") is not None
    assert golang_pattern.search("Looking for a Go Lang engineer") is not None
    assert golang_pattern.search("Must have good communication skills") is None
    assert golang_pattern.search("We are going to launch soon") is None

    # Test 'Java' regex does not match 'JavaScript'
    java_pattern = re.compile(TECH_SKILLS_CATALOG["Java"].regex_pattern, re.IGNORECASE)
    assert java_pattern.search("Core Java backend developer") is not None
    assert java_pattern.search("Frontend JavaScript engineer") is None
