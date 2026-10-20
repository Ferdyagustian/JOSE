"""PySpark Session builder tuned for serverless and ephemeral runners.

Configured specifically to prevent Out-Of-Memory (OOM) failures in the GitHub
Actions Free Tier (2 vCPUs, 7 GB RAM limit).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def get_spark_session(app_name: str = "JobRadarSilver"):
    """Create or retrieve a tuned single-node SparkSession.

    Configured with Delta Lake ACID extensions and conservative memory limits:
      - driver.memory: 4g
      - executor.memory: 2g
      - shuffle.partitions: 4 (reduced from default 200 for single-node efficiency)
      - spark.ui.enabled: false (eliminate web UI memory overhead)
    """
    try:
        from delta import configure_spark_with_delta_pip
        from pyspark.sql import SparkSession

        # JVM module open flags for Java 17 compatibility
        java_opts = (
            "--add-opens=java.base/java.lang=ALL-UNNAMED "
            "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
            "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
            "--add-opens=java.base/java.io=ALL-UNNAMED "
            "--add-opens=java.base/java.net=ALL-UNNAMED "
            "--add-opens=java.base/java.nio=ALL-UNNAMED "
            "--add-opens=java.base/java.util=ALL-UNNAMED "
            "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
            "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED"
        )
        if "_JAVA_OPTIONS" not in os.environ:
            os.environ["_JAVA_OPTIONS"] = java_opts

        builder = (
            SparkSession.builder.appName(app_name)
            .master("local[2]")
            .config("spark.driver.memory", "4g")
            .config("spark.executor.memory", "2g")
            .config("spark.sql.shuffle.partitions", "4")
            .config("spark.default.parallelism", "4")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog",
            )
            .config("spark.ui.enabled", "false")
            .config("spark.driver.extraJavaOptions", java_opts)
        )

        return configure_spark_with_delta_pip(builder).getOrCreate()

    except Exception as exc:
        logger.warning("PySpark JVM session could not be created: %s", exc)
        return None
