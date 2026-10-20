{{ config(materialized='table') }}

WITH scd_companies AS (
    SELECT * FROM {{ ref('scd_dim_companies') }}
)

SELECT
    MD5(company_name || COALESCE(CAST(dbt_valid_from AS VARCHAR), '')) AS company_key,
    company_name,
    company_location,
    company_industry,
    has_remote_policy,
    total_active_jobs,
    dbt_valid_from AS valid_from,
    dbt_valid_to AS valid_to,
    (dbt_valid_to IS NULL) AS is_current
FROM scd_companies
