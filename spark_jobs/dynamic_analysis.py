import os
import numpy as np
from spark_jobs.spark_session import spark
from pyspark.sql.functions import (
    col, sum as spark_sum, count as spark_count, mean as spark_mean,
    desc, substring, max as spark_max, min as spark_min, avg as spark_avg
)
from pyspark.sql.types import NumericType, StringType, DateType, TimestampType


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

ICON_MAP = [
    "fa-chart-simple", "fa-hashtag", "fa-dollar-sign", "fa-percent",
    "fa-chart-bar", "fa-table", "fa-database", "fa-layer-group"
]
COLOR_MAP = ["primary", "info", "success", "warning", "danger", "primary", "info", "success"]

_DYN_DATASET_CACHE = {}


def _load_dynamic_df(path):
    """Cache uploaded CSV in Spark memory (reused across filter requests)."""
    abs_path = os.path.abspath(path)
    mtime = os.path.getmtime(abs_path) if os.path.exists(abs_path) else 0

    if abs_path in _DYN_DATASET_CACHE:
        cached_mtime, cached_df = _DYN_DATASET_CACHE[abs_path]
        if cached_mtime == mtime:
            return cached_df

    df = spark.read.csv(path, header=True, inferSchema=True)
    df = df.cache()
    df.count()
    _DYN_DATASET_CACHE[abs_path] = (mtime, df)
    return df


def preload_dynamic_dataset(path):
    if os.path.exists(path):
        _load_dynamic_df(path)
        return True
    return False


def _format_val(val):
    if val is None:
        return "N/A"
    if isinstance(val, float):
        return f"{val:,.2f}"
    if isinstance(val, int):
        return f"{val:,}"
    return str(val)


def _simple_forecast(values, month_nums=None):
    """Auto-selected seasonal sklearn forecast. Returns (value, trend_pct, accuracy_pct)."""
    from spark_jobs.forecasting import forecast_simple
    try:
        return forecast_simple(values, month_nums=month_nums)
    except Exception:
        return (values[-1] if values else 0.0), 0.0, 75.0


# ──────────────────────────────────────────────
# MAIN ANALYSIS FUNCTION
# ──────────────────────────────────────────────

def analyze_dataset(path, filters=None):
    """
    Fully adaptive dataset analyser.
    - filters: dict {col_name: value} – optional user-selected filter values
    """
    if not os.path.exists(path):
        return {"success": False, "error": "Dataset file not found."}

    filtered_cached = False
    try:
        base_df = _load_dynamic_df(path)
        df = base_df

        filename = os.path.basename(path)
        total_rows_full = base_df.count()
        columns = base_df.columns

        # ── Schema classification ─────────────────────────────────────────
        numeric_cols, categorical_cols, date_cols = [], [], []

        for field in df.schema.fields:
            if isinstance(field.dataType, NumericType):
                numeric_cols.append(field.name)
            elif isinstance(field.dataType, (DateType, TimestampType)):
                date_cols.append(field.name)
            elif isinstance(field.dataType, StringType):
                name_lower = field.name.lower()
                if any(k in name_lower for k in ('date', 'time', 'day', 'month', 'year')):
                    date_cols.append(field.name)
                else:
                    categorical_cols.append(field.name)

        # ── Detect low-cardinality categoricals for filter dropdowns ──────
        filter_cols = {}  # {col_name: [distinct_values]}
        for cat_col in categorical_cols[:5]:
            try:
                distinct_count = df.select(cat_col).distinct().count()
                if 2 <= distinct_count <= 40:
                    vals = [
                        str(r[cat_col])
                        for r in df.select(cat_col).distinct().orderBy(cat_col).collect()
                        if r[cat_col] is not None
                    ]
                    filter_cols[cat_col] = vals
                    if len(filter_cols) == 3:
                        break
            except Exception:
                pass

        # ── Apply user filters ────────────────────────────────────────────
        if filters:
            for col_name, col_val in filters.items():
                if col_val and col_val != "All" and col_name in columns:
                    df = df.filter(col(col_name) == col_val)
            df = df.cache()
            filtered_cached = True

        total_rows = df.count()
        shape = f"{total_rows:,} rows × {len(columns)} columns"

        # ── Top 10 rows by primary numeric column ─────────────────────────
        if numeric_cols:
            preview_data = [
                row.asDict()
                for row in df.orderBy(desc(col(numeric_cols[0]))).limit(10).collect()
            ]
            preview_sort_col = numeric_cols[0]
        else:
            preview_data = [row.asDict() for row in df.limit(10).collect()]
            preview_sort_col = None

        # ── KPI cards (top 4 numeric totals) ─────────────────────────────
        kpis = []
        for i, num_col in enumerate(numeric_cols[:4]):
            try:
                val = df.select(spark_sum(col(num_col))).collect()[0][0]
                if val is not None:
                    kpis.append({
                        "title": f"Total {num_col}",
                        "value": _format_val(val),
                        "icon": ICON_MAP[i % len(ICON_MAP)],
                        "color": COLOR_MAP[i % len(COLOR_MAP)],
                        "trend": "up",
                        "id": f"kpi_{i}"
                    })
            except Exception:
                pass

        # Fallback: row count
        if not kpis:
            kpis.append({
                "title": "Total Records",
                "value": f"{total_rows:,}",
                "icon": "fa-table",
                "color": "primary",
                "trend": "up",
                "id": "kpi_0"
            })

        # ── Charts ────────────────────────────────────────────────────────
        charts = []
        chart_id = 0

        # 1. Time-series trend (line) — always try first
        if date_cols and numeric_cols:
            try:
                date_col = date_cols[0]
                num_col = numeric_cols[0]
                time_df = (
                    df.groupBy(substring(col(date_col).cast("string"), 1, 7).alias("period"))
                    .agg(spark_sum(col(num_col)).alias("val"))
                    .orderBy("period")
                    .limit(36)
                    .collect()
                )
                labels = [str(r["period"]) for r in time_df]
                values = [float(r["val"]) if r["val"] is not None else 0.0 for r in time_df]

                if labels:
                    charts.append({
                        "id": f"chart_{chart_id}",
                        "title": f"{num_col} Trend Over Time",
                        "type": "line",
                        "labels": labels,
                        "values": values
                    })
                    chart_id += 1
            except Exception:
                pass

        # 2. Top categorical by primary numeric (bar)
        if categorical_cols and numeric_cols:
            try:
                cat_col = categorical_cols[0]
                num_col = numeric_cols[0]
                agg_alias = f"sum_{num_col.replace(' ', '_')}"
                cat_df = (
                    df.groupBy(col(cat_col))
                    .agg(spark_sum(col(num_col)).alias(agg_alias))
                    .orderBy(desc(agg_alias))
                    .limit(10)
                    .collect()
                )
                labels = [str(r[cat_col]) for r in cat_df]
                values = [float(r[agg_alias]) if r[agg_alias] is not None else 0.0 for r in cat_df]

                if labels:
                    charts.append({
                        "id": f"chart_{chart_id}",
                        "title": f"Top {cat_col} by {num_col}",
                        "type": "bar",
                        "labels": labels,
                        "values": values
                    })
                    chart_id += 1
            except Exception:
                pass

        # 3. Second categorical distribution (doughnut)
        if len(categorical_cols) > 1:
            try:
                cat_col2 = categorical_cols[1]
                cat_df2 = (
                    df.groupBy(col(cat_col2))
                    .agg(spark_count("*").alias("cnt"))
                    .orderBy(desc("cnt"))
                    .limit(10)
                    .collect()
                )
                labels = [str(r[cat_col2]) for r in cat_df2]
                values = [float(r["cnt"]) for r in cat_df2]

                if labels:
                    charts.append({
                        "id": f"chart_{chart_id}",
                        "title": f"Distribution by {cat_col2}",
                        "type": "doughnut",
                        "labels": labels,
                        "values": values
                    })
                    chart_id += 1
            except Exception:
                pass

        # 4. Third categorical (pie)
        if len(categorical_cols) > 2:
            try:
                cat_col3 = categorical_cols[2]
                cat_df3 = (
                    df.groupBy(col(cat_col3))
                    .agg(spark_count("*").alias("cnt"))
                    .orderBy(desc("cnt"))
                    .limit(8)
                    .collect()
                )
                labels = [str(r[cat_col3]) for r in cat_df3]
                values = [float(r["cnt"]) for r in cat_df3]

                if labels:
                    charts.append({
                        "id": f"chart_{chart_id}",
                        "title": f"Distribution by {cat_col3}",
                        "type": "pie",
                        "labels": labels,
                        "values": values
                    })
                    chart_id += 1
            except Exception:
                pass

        # ── Top Items table ───────────────────────────────────────────────
        # Find best text col + best numeric col pair
        top_items = []
        top_items_label_col = None
        top_items_value_col = None

        if categorical_cols and numeric_cols:
            try:
                label_col = categorical_cols[0]
                val_col = numeric_cols[0]
                top_items_label_col = label_col
                top_items_value_col = val_col

                agg_alias2 = f"total_{val_col.replace(' ', '_')}"
                raw = (
                    df.groupBy(col(label_col))
                    .agg(spark_sum(col(val_col)).alias(agg_alias2))
                    .orderBy(desc(agg_alias2))
                    .limit(10)
                    .collect()
                )
                for r in raw:
                    top_items.append({
                        "label": str(r[label_col]),
                        "value": _format_val(r[agg_alias2]),
                        "raw": float(r[agg_alias2]) if r[agg_alias2] is not None else 0.0
                    })
            except Exception:
                pass

        # ── ML Forecast ───────────────────────────────────────────────────
        forecast = None
        if date_cols and numeric_cols:
            try:
                date_col = date_cols[0]
                num_col = numeric_cols[0]
                time_vals = (
                    df.groupBy(substring(col(date_col).cast("string"), 1, 7).alias("period"))
                    .agg(spark_sum(col(num_col)).alias("val"))
                    .orderBy("period")
                    .limit(36)
                    .collect()
                )
                vals_list = []
                month_nums = []
                for r in time_vals:
                    if r["val"] is None:
                        continue
                    vals_list.append(float(r["val"]))
                    period = str(r["period"])
                    if len(period) >= 7 and period[4] == "-":
                        try:
                            month_nums.append(int(period[5:7]))
                        except ValueError:
                            month_nums.append(((len(month_nums) % 12) + 1))
                    else:
                        month_nums.append(((len(month_nums) % 12) + 1))
                if len(vals_list) >= 2:
                    fval, ftrend, facc = _simple_forecast(vals_list, month_nums=month_nums)
                    forecast = {
                        "value": _format_val(fval),
                        "trend": f"{'+' if ftrend >= 0 else ''}{ftrend}%",
                        "trend_class": "up" if ftrend >= 0 else "down",
                        "accuracy": f"{facc}%",
                        "label": f"Next Period {num_col}"
                    }
            except Exception:
                pass

        # ── AI Insights ───────────────────────────────────────────────────
        insights = []
        if categorical_cols:
            try:
                top_cat = (
                    df.groupBy(col(categorical_cols[0]))
                    .count()
                    .orderBy(desc("count"))
                    .first()
                )
                insights.append({
                    "title": f"Top {categorical_cols[0]}",
                    "value": str(top_cat[categorical_cols[0]]),
                    "desc": f"Highest frequency — {top_cat['count']:,} records",
                    "icon": "fa-star"
                })
            except Exception:
                pass

        if numeric_cols:
            try:
                avg_val = df.select(spark_avg(col(numeric_cols[0]))).first()[0]
                insights.append({
                    "title": f"Avg {numeric_cols[0]}",
                    "value": _format_val(avg_val),
                    "desc": "Dataset average across all records",
                    "icon": "fa-calculator"
                })
            except Exception:
                pass

        if numeric_cols:
            try:
                max_val = df.select(spark_max(col(numeric_cols[0]))).first()[0]
                insights.append({
                    "title": f"Peak {numeric_cols[0]}",
                    "value": _format_val(max_val),
                    "desc": "Maximum single value in dataset",
                    "icon": "fa-arrow-trend-up"
                })
            except Exception:
                pass

        return {
            "success": True,
            "filename": filename,
            "shape": shape,
            "total_rows": total_rows,
            "columns": columns,
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
            "date_cols": date_cols,
            "filter_cols": filter_cols,
            "preview_data": preview_data,
            "preview_sort_col": preview_sort_col,
            "kpis": kpis,
            "charts": charts,
            "top_items": top_items,
            "top_items_label_col": top_items_label_col,
            "top_items_value_col": top_items_value_col,
            "forecast": forecast,
            "insights": insights
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
    finally:
        if filtered_cached:
            try:
                df.unpersist()
            except Exception:
                pass
