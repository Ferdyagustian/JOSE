{{ config(materialized='table') }}

WITH jobs AS (
    SELECT * FROM {{ ref('stg_jobs') }}
),

companies AS (
    SELECT
        company_key,
        company_name
    FROM {{ ref('dim_companies') }}
    WHERE is_current = true
)

SELECT
    MD5(j.job_id) AS job_key,
    j.job_id,
    COALESCE(c.company_key, MD5(j.company_name)) AS company_key,
    j.company_name,
    j.source_portal,
    j.job_title,
    j.role_category,
    j.employment_type,
    j.experience_level,
    j.work_policy,
    j.company_location,
    j.salary_min_idr,
    j.salary_max_idr,
    CASE
        WHEN j.salary_min_idr IS NOT NULL AND j.salary_max_idr IS NOT NULL
            THEN (j.salary_min_idr + j.salary_max_idr) / 2
        WHEN j.salary_min_idr IS NOT NULL
            THEN j.salary_min_idr
        WHEN j.salary_max_idr IS NOT NULL
            THEN j.salary_max_idr
        ELSE NULL
    END AS salary_avg_idr,
    (j.salary_min_idr IS NOT NULL AND j.salary_min_idr > 0) AS has_salary_disclosed,
    j.posted_at AS posted_date,
    j.job_url,
    j.job_description
FROM jobs j
LEFT JOIN companies c
    ON j.company_name = c.company_name
