"""
Shared PySpark session with lazy init and JVM reconnect.

Flask debug reloader (and Windows process restarts) can kill the Spark JVM
while Python still holds a dead Py4J connection — causing ConnectionRefusedError.
"""
import os
import sys

# Remove incorrect Spark path
os.environ.pop("SPARK_HOME", None)

# Configure Java
os.environ["JAVA_HOME"] = r"C:\Program Files\Java\jdk-17"

# Update PATH
os.environ["PATH"] = os.environ["JAVA_HOME"] + r"\bin;" + os.environ["PATH"]

# Configure Python for PySpark
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

from pyspark.sql import SparkSession

_spark = None


def _should_init_spark():
    """Avoid starting Spark in the Werkzeug reloader parent watcher process."""
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return True
    # No reloader active (e.g. use_reloader=False or production server)
    if os.environ.get("WERKZEUG_RUN_MAIN") is None:
        return True
    return False


def _create_spark():
    session = (
        SparkSession.builder
        .master("local[*]")
        .appName("EcommerceAnalytics")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.port", "0")
        .config("spark.blockManager.port", "0")
        .config("spark.port.maxRetries", "100")
        # Faster local runs on small CSV datasets (~30k rows)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.default.parallelism", "4")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("ERROR")
    return session


def warm_spark():
    """Start JVM + Spark now so the first dashboard click is not blocked."""
    session = get_spark()
    session.range(1).count()
    return session


def _is_spark_alive(session):
    try:
        session.sparkContext.sparkUser()
        return True
    except Exception:
        return False


def get_spark():
    """Return a live SparkSession, recreating it if the JVM connection died."""
    global _spark

    if not _should_init_spark():
        raise RuntimeError(
            "Spark is not available in the Flask reloader parent process. "
            "Use use_reloader=False when running app.py."
        )

    if _spark is not None and _is_spark_alive(_spark):
        return _spark

    if _spark is not None:
        try:
            _spark.stop()
        except Exception:
            pass
        _spark = None

    _spark = _create_spark()
    return _spark


class _SparkProxy:
    """Transparent proxy so existing `spark.read` imports keep working."""

    def __getattr__(self, name):
        return getattr(get_spark(), name)


spark = _SparkProxy()
