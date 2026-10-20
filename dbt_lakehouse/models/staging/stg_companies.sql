{{ config(materialized='view') }}

WITH jobs AS (
    SELECT * FROM {{ ref('stg_jobs') }}
),

company_aggregates AS (
    SELECT
        company_name,
        COALESCE(MODE(company_location), 'Indonesia') AS company_location,
        COALESCE(MODE(company_industry), 'Technology') AS company_industry,
        BOOL_OR(work_policy IN ('Remote', 'Hybrid')) AS has_remote_policy,
        COUNT(job_id) AS total_active_jobs,
        MAX(updated_at) AS last_seen_at
    FROM jobs
    WHERE company_name IS NOT NULL AND TRIM(company_name) != ''
    GROUP BY company_name
)

SELECT
    company_name,
    company_location,
    company_industry,
    has_remote_policy,
    total_active_jobs,
    last_seen_at
FROM company_aggregates
