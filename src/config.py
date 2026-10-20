"""Central configuration module.

Provides environment settings, storage paths, and the master dictionary of technical
skills with regex matching rules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Base workspace directory
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
load_dotenv(ROOT_DIR / ".env")


class Settings:
    """Application settings with environment variable fallbacks."""

    def __init__(self) -> None:
        self.environment: str = os.getenv("ENVIRONMENT", "development").lower()
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.azure_storage_connection_string: str = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
        self.youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")

        # Local storage directory fallbacks
        self.local_data_dir: Path = ROOT_DIR / os.getenv("LOCAL_DATA_DIR", "data")
        self.bronze_container: str = os.getenv("BRONZE_CONTAINER_NAME", "bronze")
        self.silver_container: str = os.getenv("SILVER_CONTAINER_NAME", "silver")
        self.gold_container: str = os.getenv("GOLD_CONTAINER_NAME", "gold")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_azure_configured(self) -> bool:
        return bool(self.azure_storage_connection_string.strip())


settings = Settings()


@dataclass(frozen=True)
class SkillDefinition:
    """Definition of a monitored technical skill."""

    name: str
    category: str
    regex_pattern: str


# Master Dictionary of Technical Skills
# Regex patterns use strict word boundaries to avoid false positives (e.g. 'go' vs 'good')
TECH_SKILLS_CATALOG: dict[str, SkillDefinition] = {
    # Programming Languages
    "Python": SkillDefinition(
        name="Python",
        category="Programming Language",
        regex_pattern=r"\bpython\b",
    ),
    "SQL": SkillDefinition(
        name="SQL",
        category="Programming Language",
        regex_pattern=r"\bsql\b",
    ),
    "Golang": SkillDefinition(
        name="Golang",
        category="Programming Language",
        regex_pattern=r"\b(golang|go\s+lang)\b",
    ),
    "Java": SkillDefinition(
        name="Java",
        category="Programming Language",
        regex_pattern=r"\bjava\b(?!\s*script)",
    ),
    "Scala": SkillDefinition(
        name="Scala",
        category="Programming Language",
        regex_pattern=r"\bscala\b",
    ),
    "TypeScript": SkillDefinition(
        name="TypeScript",
        category="Programming Language",
        regex_pattern=r"\b(typescript|ts)\b",
    ),
    "JavaScript": SkillDefinition(
        name="JavaScript",
        category="Programming Language",
        regex_pattern=r"\b(javascript|js)\b",
    ),
    "R": SkillDefinition(
        name="R",
        category="Programming Language",
        regex_pattern=r"\br\s+programming|\br\s+language\b",
    ),
    "C++": SkillDefinition(
        name="C++",
        category="Programming Language",
        regex_pattern=r"\bc\+\+(?!\w)",
    ),
    "C#": SkillDefinition(
        name="C#",
        category="Programming Language",
        regex_pattern=r"\bc#(?!\w)|\bc-sharp\b",
    ),
    # Data Engineering & Streaming
    "PySpark": SkillDefinition(
        name="PySpark",
        category="Data Engineering",
        regex_pattern=r"\bpyspark\b",
    ),
    "Apache Spark": SkillDefinition(
        name="Apache Spark",
        category="Data Engineering",
        regex_pattern=r"\b(apache\s+spark|spark)\b",
    ),
    "Delta Lake": SkillDefinition(
        name="Delta Lake",
        category="Data Engineering",
        regex_pattern=r"\bdelta\s+lake\b",
    ),
    "dbt": SkillDefinition(
        name="dbt",
        category="Data Engineering",
        regex_pattern=r"\bdbt\b|\bdata\s+build\s+tool\b",
    ),
    "Airflow": SkillDefinition(
        name="Airflow",
        category="Data Engineering",
        regex_pattern=r"\b(apache\s+airflow|airflow)\b",
    ),
    "Kafka": SkillDefinition(
        name="Kafka",
        category="Data Engineering",
        regex_pattern=r"\b(apache\s+kafka|kafka)\b",
    ),
    "Flink": SkillDefinition(
        name="Flink",
        category="Data Engineering",
        regex_pattern=r"\b(apache\s+flink|flink)\b",
    ),
    "DuckDB": SkillDefinition(
        name="DuckDB",
        category="Data Engineering",
        regex_pattern=r"\bduckdb\b",
    ),
    "Snowflake": SkillDefinition(
        name="Snowflake",
        category="Data Engineering",
        regex_pattern=r"\bsnowflake\b",
    ),
    "BigQuery": SkillDefinition(
        name="BigQuery",
        category="Data Engineering",
        regex_pattern=r"\bbigquery\b",
    ),
    # Cloud & DevOps
    "Azure": SkillDefinition(
        name="Azure",
        category="Cloud & DevOps",
        regex_pattern=r"\b(azure|microsoft\s+azure|adls)\b",
    ),
    "AWS": SkillDefinition(
        name="AWS",
        category="Cloud & DevOps",
        regex_pattern=r"\b(aws|amazon\s+web\s+services)\b",
    ),
    "GCP": SkillDefinition(
        name="GCP",
        category="Cloud & DevOps",
        regex_pattern=r"\b(gcp|google\s+cloud)\b",
    ),
    "Docker": SkillDefinition(
        name="Docker",
        category="Cloud & DevOps",
        regex_pattern=r"\bdocker\b",
    ),
    "Kubernetes": SkillDefinition(
        name="Kubernetes",
        category="Cloud & DevOps",
        regex_pattern=r"\b(kubernetes|k8s)\b",
    ),
    "Terraform": SkillDefinition(
        name="Terraform",
        category="Cloud & DevOps",
        regex_pattern=r"\bterraform\b",
    ),
    "Git": SkillDefinition(
        name="Git",
        category="Cloud & DevOps",
        regex_pattern=r"\b(git|github|gitlab)\b",
    ),
    "CI/CD": SkillDefinition(
        name="CI/CD",
        category="Cloud & DevOps",
        regex_pattern=r"\b(ci/cd|ci-cd|continuous\s+integration)\b",
    ),
    # Databases
    "PostgreSQL": SkillDefinition(
        name="PostgreSQL",
        category="Database",
        regex_pattern=r"\b(postgresql|postgres)\b",
    ),
    "MySQL": SkillDefinition(
        name="MySQL",
        category="Database",
        regex_pattern=r"\bmysql\b",
    ),
    "MongoDB": SkillDefinition(
        name="MongoDB",
        category="Database",
        regex_pattern=r"\bmongodb|mongo\b",
    ),
    "Redis": SkillDefinition(
        name="Redis",
        category="Database",
        regex_pattern=r"\bredis\b",
    ),
    # Frameworks & Libraries
    "FastAPI": SkillDefinition(
        name="FastAPI",
        category="Framework",
        regex_pattern=r"\bfastapi\b",
    ),
    "Django": SkillDefinition(
        name="Django",
        category="Framework",
        regex_pattern=r"\bdjango\b",
    ),
    "React": SkillDefinition(
        name="React",
        category="Framework",
        regex_pattern=r"\breact(\.js|js)?\b",
    ),
    "Pandas": SkillDefinition(
        name="Pandas",
        category="Framework",
        regex_pattern=r"\bpandas\b",
    ),
    "Polars": SkillDefinition(
        name="Polars",
        category="Framework",
        regex_pattern=r"\bpolars\b",
    ),
    "TensorFlow": SkillDefinition(
        name="TensorFlow",
        category="Framework",
        regex_pattern=r"\btensorflow\b",
    ),
    "PyTorch": SkillDefinition(
        name="PyTorch",
        category="Framework",
        regex_pattern=r"\bpytorch\b",
    ),
}

# Monitored top skills targeted for YouTube API Radar (to prevent quota exhaustion)
MONITORED_YOUTUBE_SKILLS: list[str] = [
    "Python",
    "SQL",
    "PySpark",
    "dbt",
    "Airflow",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Golang",
    "Kafka",
    "PostgreSQL",
    "Snowflake",
    "AWS",
    "Azure",
    "FastAPI",
]
