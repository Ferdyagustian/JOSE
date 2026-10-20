{{ config(materialized='table') }}

WITH skills_from_jobs AS (
    SELECT DISTINCT
        skill_name,
        skill_category
    FROM {{ ref('stg_job_skills') }}
    WHERE skill_name IS NOT NULL
),

ranked AS (
    SELECT
        skill_name,
        skill_category,
        ROW_NUMBER() OVER (PARTITION BY skill_name ORDER BY skill_category) AS rn
    FROM skills_from_jobs
)

SELECT
    MD5(skill_name) AS skill_key,
    skill_name,
    skill_category
FROM ranked
WHERE rn = 1
