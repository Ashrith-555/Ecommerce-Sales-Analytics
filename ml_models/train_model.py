import pandas as pd

from sklearn.linear_model import LinearRegression

import joblib


def train_model():

    # LOAD DATASET
    df = pd.read_csv("sales.csv")

    # CONVERT DATE
    df["Order Date"] = pd.to_datetime(
        df["Order Date"]
    )

    # CREATE MONTH COLUMN
    df["Month"] = df["Order Date"].dt.month

    # INPUT
    X = df[["Month"]]

    # OUTPUT
    y = df["Sales"]

    # MODEL
    model = LinearRegression()

    model.fit(X, y)

    # SAVE MODEL
    joblib.dump(
        model,
        "ml_models/sales_prediction.pkl"
    )

    print("Model Trained Successfully")


if __name__ == "__main__":

    train_model()