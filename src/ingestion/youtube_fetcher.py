"""YouTube Data API v3 fetcher for tech skill tutorial videos.

Includes a 21-day TTL cache guard to prevent exhausting the 10,000 daily API quota,
and provides graceful fallback metadata when running offline or without API keys.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import MONITORED_YOUTUBE_SKILLS, settings
from src.ingestion.schemas import YouTubeVideoRaw
from src.ingestion.storage import (
    load_all_cached_youtube_skills,
    save_raw_youtube_videos,
)

logger = logging.getLogger(__name__)

# Curated fallback educational channels/tutorials for offline development
FALLBACK_TUTORIALS: dict[str, list[dict]] = {
    "Python": [
        {
            "video_id": "rfscVS0vtbw",
            "video_title": "Python for Beginners - Full Course [Programming Tutorial]",
            "channel_name": "FreeCodeCamp",
            "view_count": 42000000,
            "like_count": 1100000,
            "thumbnail_url": "https://i.ytimg.com/vi/rfscVS0vtbw/hqdefault.jpg",
        }
    ],
    "SQL": [
        {
            "video_id": "7S_tz1z_5bA",
            "video_title": "SQL Tutorial for Beginners [Complete Course]",
            "channel_name": "Programming with Mosh",
            "view_count": 4300000,
            "like_count": 120000,
            "thumbnail_url": "https://i.ytimg.com/vi/7S_tz1z_5bA/hqdefault.jpg",
        }
    ],
    "PostgreSQL": [
        {
            "video_id": "qw--VYLpxG4",
            "video_title": "PostgreSQL Tutorial Full Course 2024",
            "channel_name": "FreeCodeCamp",
            "view_count": 2100000,
            "like_count": 52000,
            "thumbnail_url": "https://i.ytimg.com/vi/qw--VYLpxG4/hqdefault.jpg",
        }
    ],
    "Docker": [
        {
            "video_id": "fqMOX6JJhGo",
            "video_title": "Docker Tutorial for Beginners [Full Course]",
            "channel_name": "TechWorld with Nana",
            "view_count": 6200000,
            "like_count": 190000,
            "thumbnail_url": "https://i.ytimg.com/vi/fqMOX6JJhGo/hqdefault.jpg",
        }
    ],
    "Kubernetes": [
        {
            "video_id": "X48VuDVv0do",
            "video_title": "Kubernetes Tutorial for Beginners [Full Course in 4 Hours]",
            "channel_name": "TechWorld with Nana",
            "view_count": 4100000,
            "like_count": 130000,
            "thumbnail_url": "https://i.ytimg.com/vi/X48VuDVv0do/hqdefault.jpg",
        }
    ],
    "AWS": [
        {
            "video_id": "k1RI5locZE4",
            "video_title": "AWS Certified Cloud Practitioner Certification Course (CLF-C02)",
            "channel_name": "FreeCodeCamp",
            "view_count": 3200000,
            "like_count": 78000,
            "thumbnail_url": "https://i.ytimg.com/vi/k1RI5locZE4/hqdefault.jpg",
        }
    ],
    "Azure": [
        {
            "video_id": "3hLmDS179YE",
            "video_title": "Microsoft Azure Fundamentals Certification Course (AZ-900)",
            "channel_name": "FreeCodeCamp",
            "view_count": 1800000,
            "like_count": 45000,
            "thumbnail_url": "https://i.ytimg.com/vi/3hLmDS179YE/hqdefault.jpg",
        }
    ],
    "PySpark": [
        {
            "video_id": "XrpSRCwISdk",
            "video_title": "PySpark Tutorial for Beginners | Apache Spark with Python",
            "channel_name": "FreeCodeCamp",
            "view_count": 350000,
            "like_count": 12000,
            "thumbnail_url": "https://i.ytimg.com/vi/XrpSRCwISdk/hqdefault.jpg",
        }
    ],
    "dbt": [
        {
            "video_id": "b2nSMPiXdXk",
            "video_title": "What is dbt? Complete Introduction to Data Build Tool",
            "channel_name": "dbt Labs",
            "view_count": 280000,
            "like_count": 9100,
            "thumbnail_url": "https://i.ytimg.com/vi/b2nSMPiXdXk/hqdefault.jpg",
        }
    ],
    "Airflow": [
        {
            "video_id": "K9AnJ9_ZAXE",
            "video_title": "Apache Airflow Tutorial for Beginners - Full Data Engineering Course",
            "channel_name": "Marc Lamberti",
            "view_count": 640000,
            "like_count": 21000,
            "thumbnail_url": "https://i.ytimg.com/vi/K9AnJ9_ZAXE/hqdefault.jpg",
        }
    ],
    "Kafka": [
        {
            "video_id": "R873BlNVUB4",
            "video_title": "Apache Kafka Crash Course for Beginners",
            "channel_name": "Amigoscode",
            "view_count": 890000,
            "like_count": 28000,
            "thumbnail_url": "https://i.ytimg.com/vi/R873BlNVUB4/hqdefault.jpg",
        }
    ],
    "Terraform": [
        {
            "video_id": "7xngnjfIlK4",
            "video_title": "Terraform Course - Automate your AWS Cloud Infrastructure",
            "channel_name": "FreeCodeCamp",
            "view_count": 950000,
            "like_count": 31000,
            "thumbnail_url": "https://i.ytimg.com/vi/7xngnjfIlK4/hqdefault.jpg",
        }
    ],
    "Golang": [
        {
            "video_id": "YS4e4q9oBaU",
            "video_title": "Go Programming - 11 Hour Full Course for Beginners",
            "channel_name": "FreeCodeCamp",
            "view_count": 3700000,
            "like_count": 115000,
            "thumbnail_url": "https://i.ytimg.com/vi/YS4e4q9oBaU/hqdefault.jpg",
        }
    ],
    "Snowflake": [
        {
            "video_id": "Da0foVXsyTU",
            "video_title": "Snowflake Cloud Data Warehouse - Complete Masterclass",
            "channel_name": "FreeCodeCamp",
            "view_count": 520000,
            "like_count": 17000,
            "thumbnail_url": "https://i.ytimg.com/vi/Da0foVXsyTU/hqdefault.jpg",
        }
    ],
    "FastAPI": [
        {
            "video_id": "0sOvCWFmrtA",
            "video_title": "Python FastAPI Tutorial: Build a Complete REST API",
            "channel_name": "FreeCodeCamp",
            "view_count": 1600000,
            "like_count": 49000,
            "thumbnail_url": "https://i.ytimg.com/vi/0sOvCWFmrtA/hqdefault.jpg",
        }
    ],
}


class YouTubeFetcher:
    """Fetcher for YouTube tutorial videos with cache guards."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.youtube_api_key
        self.client = None
        if self.api_key and not self.api_key.startswith("AIzaSyYourMock"):
            try:
                self.client = build("youtube", "v3", developerKey=self.api_key)
            except Exception as e:
                logger.warning("Could not initialize YouTube API client: %s", e)

    def _get_fallback_videos(self, skill_name: str) -> list[YouTubeVideoRaw]:
        """Generate high-quality fallback videos when offline or quota exceeded."""
        templates = FALLBACK_TUTORIALS.get(
            skill_name,
            [
                {
                    "video_id": f"mock_{skill_name.lower()}_1",
                    "video_title": f"{skill_name} Crash Course for Developers & Engineers",
                    "channel_name": "Tech University",
                    "view_count": 150000,
                    "like_count": 4800,
                    "thumbnail_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=500&q=80",
                }
            ],
        )

        results: list[YouTubeVideoRaw] = []
        for t in templates:
            results.append(
                YouTubeVideoRaw(
                    video_id=t["video_id"],
                    skill_name=skill_name,
                    video_title=t["video_title"],
                    channel_name=t["channel_name"],
                    view_count=t["view_count"],
                    like_count=t["like_count"],
                    video_url=f"https://www.youtube.com/watch?v={t['video_id']}",
                    thumbnail_url=t["thumbnail_url"],
                    published_at=datetime.now(UTC).isoformat(),
                )
            )
        return results

    def fetch_videos_for_skill(
        self,
        skill_name: str,
        max_results: int = 5,
    ) -> list[YouTubeVideoRaw]:
        """Fetch top tutorial videos for a skill, using API or fallback."""
        if not self.client:
            logger.info("Using cached/fallback videos for skill '%s'", skill_name)
            return self._get_fallback_videos(skill_name)

        try:
            # 1. Search for top relevant tutorial videos (costs 100 quota units)
            search_response = (
                self.client.search()
                .list(
                    q=f"{skill_name} tutorial crash course",
                    part="snippet",
                    maxResults=max_results,
                    type="video",
                    relevanceLanguage="id",
                )
                .execute()
            )

            video_ids = [
                item["id"]["videoId"]
                for item in search_response.get("items", [])
                if item.get("id", {}).get("videoId")
            ]

            if not video_ids:
                return self._get_fallback_videos(skill_name)

            # 2. Get video statistics (views, likes) (costs 1 quota unit)
            stats_response = (
                self.client.videos()
                .list(
                    id=",".join(video_ids),
                    part="snippet,statistics",
                )
                .execute()
            )

            results: list[YouTubeVideoRaw] = []
            for item in stats_response.get("items", []):
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                vid = item["id"]
                thumbs = snippet.get("thumbnails", {})
                thumb_url = (
                    thumbs.get("high", {}).get("url") or thumbs.get("default", {}).get("url") or ""
                )

                results.append(
                    YouTubeVideoRaw(
                        video_id=vid,
                        skill_name=skill_name,
                        video_title=snippet.get("title", f"{skill_name} Tutorial"),
                        channel_name=snippet.get("channelTitle", "YouTube Creator"),
                        view_count=int(statistics.get("viewCount", 0)),
                        like_count=int(statistics.get("likeCount", 0)),
                        published_at=snippet.get("publishedAt"),
                        video_url=f"https://www.youtube.com/watch?v={vid}",
                        thumbnail_url=thumb_url,
                    )
                )

            return results

        except HttpError as http_err:
            logger.warning(
                "YouTube API HttpError for skill '%s' (Status %s): %s. Falling back.",
                skill_name,
                http_err.status_code,
                http_err,
            )
            return self._get_fallback_videos(skill_name)
        except Exception as err:
            logger.warning("YouTube fetch error for '%s': %s. Falling back.", skill_name, err)
            return self._get_fallback_videos(skill_name)

    def run_pipeline(
        self,
        target_skills: Sequence[str] | None = None,
        force_refresh: bool = False,
    ) -> list[YouTubeVideoRaw]:
        """Fetch tutorials for target skills, skipping skills that are already cached."""
        skills = list(target_skills or MONITORED_YOUTUBE_SKILLS)
        cached_skills = set() if force_refresh else load_all_cached_youtube_skills()

        all_videos: list[YouTubeVideoRaw] = []
        for skill in skills:
            if skill in cached_skills:
                logger.info("Skill '%s' already cached in Bronze. Skipping API call.", skill)
                continue

            videos = self.fetch_videos_for_skill(skill)
            all_videos.extend(videos)

        if all_videos:
            save_raw_youtube_videos(all_videos)

        return all_videos
