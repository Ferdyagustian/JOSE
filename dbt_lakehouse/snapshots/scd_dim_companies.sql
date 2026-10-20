{% snapshot scd_dim_companies %}

{{
    config(
      target_schema='main',
      unique_key='company_name',
      strategy='check',
      check_cols=['company_location', 'company_industry', 'has_remote_policy']
    )
}}

SELECT
    company_name,
    company_location,
    company_industry,
    has_remote_policy,
    total_active_jobs,
    last_seen_at
FROM {{ ref('stg_companies') }}

{% endsnapshot %}
