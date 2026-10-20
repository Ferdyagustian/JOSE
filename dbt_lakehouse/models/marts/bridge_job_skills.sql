{{ config(materialized='table') }}

WITH job_skills AS (
    SELECT * FROM {{ ref('stg_job_skills') }}
),

distinct_pairs AS (
    SELECT DISTINCT
        job_id,
        skill_name,
        skill_category
    FROM job_skills
)

SELECT
    MD5(job_id) AS job_key,
    MD5(skill_name) AS skill_key,
    skill_name,
    skill_category
FROM distinct_pairs
