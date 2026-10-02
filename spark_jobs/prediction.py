from pyspark.sql.functions import year, month, sum as spark_sum
from spark_jobs.forecasting import forecast_time_series, MONTHS_MAP


def generate_dynamic_forecast(filtered_df):
    """
    Generates sales forecast using auto-selected sklearn models on
    Spark-aggregated monthly sales (fast — only dozens of rows).
    """
    try:
        monthly_data = (
            filtered_df.withColumn("Year", year("Order Date"))
            .withColumn("MonthNum", month("Order Date"))
            .groupBy("Year", "MonthNum")
            .agg(spark_sum("Sales").alias("MonthlySales"))
            .orderBy("Year", "MonthNum")
            .collect()
        )

        if not monthly_data:
            return {
                "forecast_value": 0.0,
                "forecast_accuracy": 0.0,
                "forecast_trend": 0.0,
                "trend_class": "up",
                "historical_labels": [],
                "historical_values": [],
                "forecast_labels": [],
                "forecast_values": [],
            }

        monthly_data = sorted(monthly_data, key=lambda r: (r["Year"], r["MonthNum"]))

        historical_labels = []
        historical_values = []
        month_nums = []

        for r in monthly_data:
            historical_labels.append(f"{MONTHS_MAP[r['MonthNum']]} {r['Year']}")
            historical_values.append(float(r["MonthlySales"]))
            month_nums.append(int(r["MonthNum"]))

        last_row = monthly_data[-1]
        result = forecast_time_series(
            historical_values,
            month_nums=month_nums,
            horizon=3,
            last_year=last_row["Year"],
            last_month=last_row["MonthNum"],
        )

        # Preserve exact labels built from Spark rows (cleaner than reconstructed)
        result["historical_labels"] = historical_labels

        return {
            "forecast_value": result["forecast_value"],
            "forecast_accuracy": result["forecast_accuracy"],
            "forecast_trend": result["forecast_trend"],
            "trend_class": result["trend_class"],
            "historical_labels": result["historical_labels"],
            "historical_values": result["historical_values"],
            "forecast_labels": result["forecast_labels"],
            "forecast_values": result["forecast_values"],
        }
    except Exception:
        import traceback
        traceback.print_exc()
        return {
            "forecast_value": 0.0,
            "forecast_accuracy": 0.0,
            "forecast_trend": 0.0,
            "trend_class": "up",
            "historical_labels": [],
            "historical_values": [],
            "forecast_labels": [],
            "forecast_values": [],
        }
