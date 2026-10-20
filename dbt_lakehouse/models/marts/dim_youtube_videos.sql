{{ config(materialized='table') }}

WITH videos AS (
    SELECT * FROM {{ ref('stg_youtube_videos') }}
)

SELECT
    MD5(video_id) AS video_key,
    MD5(skill_name) AS skill_key,
    video_id,
    skill_name,
    video_title,
    channel_name,
    view_count,
    like_count,
    video_url,
    thumbnail_url,
    published_at
FROM videos
