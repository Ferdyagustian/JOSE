{{ config(materialized='view') }}

WITH raw_silver_jobs AS (
    SELECT *
    FROM read_parquet('data/silver/delta_jobs/*.parquet')
)

SELECT
    CAST(job_id AS VARCHAR) AS job_id,
    CAST(source AS VARCHAR) AS source_portal,
    CAST(job_title AS VARCHAR) AS job_title,
    CAST(role_category AS VARCHAR) AS role_category,
    TRIM(CAST(company_name AS VARCHAR)) AS company_name,
    CAST(company_industry AS VARCHAR) AS company_industry,
    CAST(company_location AS VARCHAR) AS company_location,
    CAST(employment_type AS VARCHAR) AS employment_type,
    CAST(work_policy AS VARCHAR) AS work_policy,
    CAST(experience_level AS VARCHAR) AS experience_level,
    CASE WHEN isnan(CAST(salary_min_idr AS DOUBLE)) THEN NULL ELSE CAST(salary_min_idr AS DOUBLE) END AS salary_min_idr,
    CASE WHEN isnan(CAST(salary_max_idr AS DOUBLE)) THEN NULL ELSE CAST(salary_max_idr AS DOUBLE) END AS salary_max_idr,
    CAST(job_description AS VARCHAR) AS job_description,
    CAST(job_url AS VARCHAR) AS job_url,
    CAST(posted_at AS VARCHAR) AS posted_at,
    CAST(updated_at AS VARCHAR) AS updated_at
FROM raw_silver_jobs
