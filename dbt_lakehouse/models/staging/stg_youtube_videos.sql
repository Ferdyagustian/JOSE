{{ config(materialized='view') }}

WITH raw_youtube AS (
    SELECT *
    FROM read_parquet('data/bronze/youtube/**/*.parquet')
),

deduped_videos AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY video_id
            ORDER BY view_count DESC
        ) AS rn
    FROM raw_youtube
)

SELECT
    CAST(video_id AS VARCHAR) AS video_id,
    TRIM(CAST(skill_name AS VARCHAR)) AS skill_name,
    CAST(video_title AS VARCHAR) AS video_title,
    CAST(channel_name AS VARCHAR) AS channel_name,
    CAST(view_count AS BIGINT) AS view_count,
    CAST(like_count AS BIGINT) AS like_count,
    CAST(video_url AS VARCHAR) AS video_url,
    CAST(thumbnail_url AS VARCHAR) AS thumbnail_url,
    CAST(published_at AS VARCHAR) AS published_at
FROM deduped_videos
WHERE rn = 1
