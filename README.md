# JOSE (Job Seeks Era)
### Indonesian Tech Job Market & YouTube Learning Radar

[![CI Quality Gate](https://github.com/Ferdyagustian/JOSE/actions/workflows/ci_quality.yml/badge.svg)](https://github.com/Ferdyagustian/JOSE/actions/workflows/ci_quality.yml)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.1-FFF000?logo=duckdb&logoColor=black)](https://duckdb.org/)
[![dbt](https://img.shields.io/badge/dbt-core%201.8-FF694B?logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![PySpark](https://img.shields.io/badge/Apache%20Spark-3.5-E25A1C?logo=apachespark&logoColor=white)](https://spark.apache.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.66-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)

A modern, serverless **Data Lakehouse** (Medallion Architecture: Bronze &rarr; Silver &rarr; Gold) engineered with the **Ponytail Philosophy** (lean, zero-overengineering, zero-burn cloud compute cost). JOSE tracks the Indonesian tech employment landscape from leading portals (Glints, JobStreet), extracts in-demand tech skills, maps them to curated YouTube tutorials, and visualizes them on a high-taste dark glassmorphism dashboard.

---

## 1. Architecture Overview

```mermaid
flowchart LR
    subgraph Ingestion ["Bronze Layer (Raw Ingestion)"]
        Glints["Glints Scraper<br/>(curl_cffi)"]
        JobStreet["JobStreet Scraper<br/>(SEEK API)"]
        YouTube["YouTube API v3<br/>(21-day TTL Guard)"]
        ColdStorage[("Bronze Parquet<br/>/ Local & Azure Blob")]
        Glints --> ColdStorage
        JobStreet --> ColdStorage
        YouTube --> ColdStorage
    end

    subgraph Processing ["Silver Layer (PySpark & Delta)"]
        SparkCleaner["PySpark Normalizer<br/>(Runner Tuned 4GB)"]
        SkillRegex["Skill Extractor<br/>(Word-boundary Regex)"]
        DeltaSilver[("Delta Lake Silver<br/>delta_jobs & delta_skills")]
        ColdStorage --> SparkCleaner
        SparkCleaner --> SkillRegex
        SkillRegex --> DeltaSilver
    end

    subgraph Modeling ["Gold Layer (dbt-core + DuckDB)"]
        dbtSnapshot["SCD Type 2 Snapshot<br/>(dim_companies)"]
        dbtMarts["Star Schema Marts<br/>(fact_job_postings, bridge)"]
        DuckDBGold[("Gold Lakehouse<br/>lakehouse.duckdb (~4.4 MB)")]
        DeltaSilver --> dbtSnapshot
        DeltaSilver --> dbtMarts
        dbtSnapshot --> DuckDBGold
        dbtMarts --> DuckDBGold
    end

    subgraph Presentation ["Analytics & BI (Streamlit)"]
        Queries["Sub-50ms Cached Engine<br/>(@st.cache_data)"]
        GlassmorphismUI["Glassmorphism Web UI<br/>(Obsidian & Slate Theme)"]
        DuckDBGold --> Queries
        Queries --> GlassmorphismUI
    end
```

---

## 2. Key Engineering Highlights

- **$0 Cloud Compute Cost:** Operates 100% within free-tier boundaries (GitHub Actions Ubuntu runner + local/Azure cold storage + DuckDB in-process engine + Streamlit Community Cloud).
- **Anti-Bot Resilient Ingestion:** Uses `curl_cffi` with Chrome 120 browser TLS fingerprint impersonation and circuit-breaker backoffs to prevent portal blocking.
- **Quota-Guarded YouTube Radar:** Integrates YouTube Data API v3 with a 21-day TTL parquet cache guard and resilient offline fallback templates (FreeCodeCamp, Programming with Mosh) ensuring 0 downtime even if quotas expire.
- **Tuned Single-Node PySpark:** Tuned for 7 GB memory runners (`spark.driver.memory="4g"`, `shuffle.partitions=4`) avoiding JVM Out-Of-Memory exceptions.
- **Strict Skill Extraction:** Regex word-boundary patterns (`\b(?i){skill}\b`) prevent false positives (e.g., distinguishing "Go" from "Good", "C" from "CV/CEO", with clean handling of "C++" and "C#").
- **Kimball Dimensional Modeling:**
  - `dim_companies`: Slowly Changing Dimension (SCD Type 2) tracking historical work policy and location updates.
  - `fact_job_postings`: Clean transaction grain with normalized Rupiah salaries (`Rp X - Y` or explicit `"Gaji tidak ditampilkan"`).
  - `bridge_job_skills`: Many-to-many relationship bridging postings and technical competencies.
- **Responsive In-Page Filter UI:** Immediate job exploration and filtering (Role, Work Policy, Employment Type including **Internship**, and keyword search) directly accessible on mobile and desktop viewports.

---

## 3. Repository Structure

```text
JOSE/
├── .github/workflows/
│   ├── ci_quality.yml           # Automated PR/Push tests (Ruff, Pytest, dbt compile)
│   └── daily_lakehouse_elt.yml  # Scheduled daily cron ELT pipeline (06:00 WIB)
├── .streamlit/
│   └── config.toml              # Streamlit Cloud dark theme & performance config
├── dashboard/
│   ├── app.py                   # Main Streamlit application
│   ├── queries.py               # Cached analytical DuckDB query engine (<50ms)
│   └── styles.py                # Deep Obsidian Glassmorphism CSS design system
├── data/
│   └── gold/
│       └── lakehouse.duckdb     # Curated production Gold database (~4.4 MB)
├── dbt_lakehouse/
│   ├── models/                  # Staging and Star Schema dimensional models
│   ├── snapshots/               # SCD Type 2 snapshot for dim_companies
│   ├── dbt_project.yml          # dbt configuration
│   └── profiles.yml             # DuckDB adapter profile
├── infra/
│   ├── main.tf                  # Optional Terraform for Azure ADLS Gen2
│   ├── variables.tf
│   └── outputs.tf
├── src/
│   ├── config.py                # Master tech skills catalog & environment loader
│   ├── ingestion/               # Glints, JobStreet, YouTube, & Azure storage
│   └── spark_jobs/              # PySpark Silver cleaner & Skill extractor
├── tests/                       # 45 unit tests (100% green pass rate)
├── .env.example                 # Template for local environment variables
├── .gitignore                   # Ponytail lean rules (protects secrets, tracks gold DB)
├── pyproject.toml               # Ruff and Pytest tooling configuration
└── requirements.txt             # Project dependencies
```

---

## 4. Quickstart Guide

### Prerequisites
- Python **3.12+**
- Java **17+** (Required only for local PySpark execution)

### 1. Clone & Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/Ferdyagustian/JOSE.git
cd JOSE

# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run the Streamlit Dashboard Locally
```bash
streamlit run dashboard/app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser. The dashboard reads directly from the pre-built Gold Lakehouse (`data/gold/lakehouse.duckdb`).

### 3. Run the Test Suite & Linter
```bash
# Run 45 unit tests across ingestion, transformations, dbt, and dashboard
pytest tests/ -v

# Run code linter
ruff check .
```

---

## 5. Running the Data Pipeline (ELT)

You can run each medallion stage individually:

```bash
# Stage 1: Bronze Ingestion (Glints, JobStreet, YouTube)
python -m src.ingestion.pipeline

# Stage 2: Silver Normalization & Delta Merge (PySpark)
python -m src.spark_jobs.bronze_to_silver_jobs

# Stage 3: Gold Modeling & SCD Type 2 Snapshots (dbt)
dbt snapshot --project-dir dbt_lakehouse --profiles-dir dbt_lakehouse
dbt run --project-dir dbt_lakehouse --profiles-dir dbt_lakehouse
dbt test --project-dir dbt_lakehouse --profiles-dir dbt_lakehouse
```

---

## 6. Environment Configuration (`.env`)

Create a `.env` file in the project root (automatically ignored by `.gitignore`):

| Variable | Description | Default | Required |
|---|---|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Blob / ADLS Gen2 connection string | Empty (uses local disk) | Optional |
| `YOUTUBE_API_KEY` | Google Cloud YouTube Data API v3 key | Empty (uses cached fallback) | Optional |
| `ENVIRONMENT` | Runtime environment (`development` / `production`) | `development` | Optional |
| `LOCAL_DATA_DIR` | Local root directory for Lakehouse partitions | `./data` | Optional |
| `BRONZE_CONTAINER_NAME` | Container name for Bronze layer | `bronze` | Optional |

---

## 7. CI/CD & Deployment

- **GitHub Actions Quality Gate (`ci_quality.yml`):** Automatically tests and lints every pull request and push to `main`.
- **Daily Automated Refresh (`daily_lakehouse_elt.yml`):** Runs daily at **06:00 WIB (23:00 UTC)**, pulls fresh postings, updates models, and auto-commits the refreshed `lakehouse.duckdb` directly to GitHub.
- **Streamlit Community Cloud:** Connect `https://github.com/Ferdyagustian/JOSE` with main file path `dashboard/app.py` for free $0 hosting.

---

## 8. License

Distributed under the **MIT License**. See `LICENSE` for more information.
