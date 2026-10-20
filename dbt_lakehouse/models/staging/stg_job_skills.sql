{{ config(materialized='view') }}

WITH raw_silver_skills AS (
    SELECT *
    FROM read_parquet('data/silver/delta_job_skills/*.parquet')
)

SELECT
    CAST(job_id AS VARCHAR) AS job_id,
    CAST(skill_id AS VARCHAR) AS skill_id,
    TRIM(CAST(skill_name AS VARCHAR)) AS skill_name,
    CAST(skill_category AS VARCHAR) AS skill_category
FROM raw_silver_skills
WHERE skill_name IS NOT NULL AND TRIM(skill_name) != ''
