from spark_jobs.spark_session import spark


def clean_data(path):

    df = spark.read.csv(
        path,
        header=True,
        inferSchema=True
    )

    df = df.dropna()

    df = df.dropDuplicates()

    return df