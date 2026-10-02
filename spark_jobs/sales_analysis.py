import os
from spark_jobs.spark_session import spark

from pyspark.sql.functions import (
    sum,
    avg,
    col,
    desc,
    to_date,
    date_format,
    coalesce,
    year as spark_year,
    month as spark_month,
)

# In-memory Spark cache: path -> (file_mtime, DataFrame)
_DATASET_CACHE = {}


def _dataset_key(path):
    return os.path.abspath(path)


def _read_and_transform_csv(path):
    df = spark.read.csv(path, header=True, inferSchema=True)

    df = df.withColumn(
        "Order Date",
        coalesce(
            to_date(col("Order Date"), "MM/dd/yyyy"),
            to_date(col("Order Date"), "MM-dd-yyyy"),
        ),
    )

    df = df.withColumn("Month", date_format(col("Order Date"), "MMM"))
    df = df.withColumn("Year", spark_year(col("Order Date")))
    df = df.withColumn("month_num", spark_month(col("Order Date")))
    df = df.withColumn("Sales", col("Sales").cast("double"))
    df = df.withColumn("Profit", col("Profit").cast("double"))
    df = df.withColumn("Discount", col("Discount").cast("double"))

    return df


def load_data(path, use_cache=True):
    """Load CSV with parsed columns; cache in Spark memory after first read."""
    abs_path = _dataset_key(path)
    mtime = os.path.getmtime(abs_path) if os.path.exists(abs_path) else 0

    if use_cache and abs_path in _DATASET_CACHE:
        cached_mtime, cached_df = _DATASET_CACHE[abs_path]
        if cached_mtime == mtime:
            return cached_df

    df = _read_and_transform_csv(path)
    df = df.cache()
    df.count()  # materialize once — later requests skip CSV parse

    _DATASET_CACHE[abs_path] = (mtime, df)
    return df


def preload_dataset(path):
    """Warm-load dataset at server startup (called from app.py)."""
    if os.path.exists(path):
        load_data(path)
        return True
    return False


def clear_dataset_cache(path=None):
    """Drop cached dataframe(s) when file changes on disk."""
    if path is None:
        for _, (_, cached_df) in list(_DATASET_CACHE.items()):
            try:
                cached_df.unpersist()
            except Exception:
                pass
        _DATASET_CACHE.clear()
        return

    abs_path = _dataset_key(path)
    if abs_path in _DATASET_CACHE:
        _, cached_df = _DATASET_CACHE.pop(abs_path)
        try:
            cached_df.unpersist()
        except Exception:
            pass


# TOTAL SALES

def get_total_sales(path):

    df = load_data(path)

    total = df.select(

        sum("Sales")

    ).collect()[0][0]

    return round(total, 2)


# TOTAL PROFIT

def get_total_profit(path):

    df = load_data(path)

    total = df.select(

        sum("Profit")

    ).collect()[0][0]

    return round(total, 2)


# TOTAL ORDERS

def get_total_orders(path):

    df = load_data(path)

    return df.count()


# AVG DISCOUNT

def get_avg_discount(path):

    df = load_data(path)

    discount = df.select(

        avg("Discount")

    ).collect()[0][0]

    return round(discount * 100, 2)


# REGION SALES

def get_region_sales(path):

    df = load_data(path)

    region_sales = df.groupBy(

        "Region"

    ).sum("Sales") \
    .withColumnRenamed(

        "sum(Sales)",

        "total_sales"
    )

    return region_sales.collect()


# CATEGORY SALES

def get_category_sales(path):

    df = load_data(path)

    category_sales = df.groupBy(

        "Category"

    ).sum("Sales") \
    .withColumnRenamed(

        "sum(Sales)",

        "total_sales"
    )

    return category_sales.collect()


# SEGMENT SALES

def get_segment_sales(path):

    df = load_data(path)

    segment_sales = df.groupBy(

        "Segment"

    ).sum("Sales") \
    .withColumnRenamed(

        "sum(Sales)",

        "total_sales"
    )

    return segment_sales.collect()


# MONTHLY SALES
def get_monthly_sales(path):
    df = load_data(path)
    monthly_sales = (
        df.groupBy("Month", "month_num")
        .sum("Sales")
        .withColumnRenamed("sum(Sales)", "monthly_sales")
        .orderBy("month_num")
    )
    return monthly_sales.collect()


# TOP PRODUCTS

def get_top_products(path):

    df = load_data(path)

    top_products = df.groupBy(

        "Product Name"

    ).sum("Sales", "Profit") \
    .withColumnRenamed(

        "sum(Sales)",

        "total_sales"
    ) \
    .withColumnRenamed(

        "sum(Profit)",

        "total_profit"
    ) \
    .orderBy(

        desc("total_sales")
    ) \
    .limit(5)

    return top_products.collect()


def get_filtered_dashboard_data(path, year_filter=None, region_filter=None, category_filter=None, search_query=None):
    from pyspark.sql.functions import count as spark_count, lower as spark_lower
    from spark_jobs.prediction import generate_dynamic_forecast

    base_df = load_data(path)

    years_raw = base_df.select("Year").distinct().orderBy("Year").collect()
    years = [str(row["Year"]) for row in years_raw if row["Year"] is not None]

    df = base_df
    if year_filter and year_filter != "All":
        df = df.filter(col("Year") == int(year_filter))
    
    if region_filter and region_filter != "All":
        df = df.filter(col("Region") == region_filter)
        
    if category_filter and category_filter != "All":
        df = df.filter(col("Category") == category_filter)
        
    if search_query:
        query_cleaned = search_query.strip().lower()
        df = df.filter(
            spark_lower(col("Product Name")).contains(query_cleaned) |
            spark_lower(col("Category")).contains(query_cleaned) |
            spark_lower(col("Sub-Category")).contains(query_cleaned)
        )
        
    # Cache to optimize subsequent aggregations
    df.cache()
    
    try:
        # 4. Calculate KPIs
        summary = df.agg(
            sum("Sales").alias("total_sales"),
            sum("Profit").alias("total_profit"),
            spark_count("Order ID").alias("total_orders"),
            avg("Discount").alias("avg_discount")
        ).collect()[0]
        
        total_sales = float(summary["total_sales"]) if summary["total_sales"] is not None else 0.0
        total_profit = float(summary["total_profit"]) if summary["total_profit"] is not None else 0.0
        total_orders = int(summary["total_orders"]) if summary["total_orders"] is not None else 0
        avg_discount = float(summary["avg_discount"]) * 100 if summary["avg_discount"] is not None else 0.0
        
        # 5. Region sales breakdown
        region_sales = df.groupBy("Region").agg(sum("Sales").alias("total_sales")).collect()
        regions = [row["Region"] for row in region_sales]
        region_values = [float(row["total_sales"]) for row in region_sales]
        
        # 6. Category sales breakdown
        category_sales = df.groupBy("Category").agg(sum("Sales").alias("total_sales")).collect()
        categories = [row["Category"] for row in category_sales]
        category_values = [float(row["total_sales"]) for row in category_sales]
        
        # 7. Monthly sales trend
        monthly_sales = df.groupBy("Month", "month_num") \
                          .agg(sum("Sales").alias("monthly_sales")) \
                          .orderBy("month_num") \
                          .collect()
        months = [row["Month"] for row in monthly_sales]
        month_values = [float(row["monthly_sales"]) for row in monthly_sales]
        
        # 8. Segment sales breakdown
        segment_sales = df.groupBy("Segment").agg(sum("Sales").alias("total_sales")).collect()
        segments = [row["Segment"] for row in segment_sales]
        segment_values = [float(row["total_sales"]) for row in segment_sales]
        
        # 9. Top products
        top_products_raw = df.groupBy("Product Name") \
                             .agg(sum("Sales").alias("total_sales"), sum("Profit").alias("total_profit")) \
                             .orderBy(desc("total_sales")) \
                             .limit(5) \
                             .collect()
        
        top_products = []
        for p in top_products_raw:
            top_products.append({
                "Product Name": p["Product Name"],
                "total_sales_raw": float(p["total_sales"]),
                "total_profit_raw": float(p["total_profit"])
            })
            
        # 10. Dynamic ML Forecast
        forecast_info = generate_dynamic_forecast(df)
        
        return {
            "success": True,
            "years": years,
            "total_sales": total_sales,
            "total_profit": total_profit,
            "total_orders": total_orders,
            "avg_discount": round(avg_discount, 2),
            "regions": regions,
            "region_values": region_values,
            "categories": categories,
            "category_values": category_values,
            "months": months,
            "month_values": month_values,
            "segments": segments,
            "segment_values": segment_values,
            "top_products": top_products,
            "forecast": forecast_info
        }
    finally:
        df.unpersist()