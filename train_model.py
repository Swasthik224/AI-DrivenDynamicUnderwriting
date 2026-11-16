import os
import joblib
import numpy as np
import pandas as pd
import shap

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    classification_report
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from xgboost import XGBClassifier

import config
from security import write_signature


NUMERIC_COLUMNS = [
    "AMT_INCOME_TOTAL",
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "REGION_POPULATION_RELATIVE",
    "DAYS_EMPLOYED",
    "DAYS_REGISTRATION",
    "DAYS_ID_PUBLISH",
    "CNT_CHILDREN",
    "CNT_FAM_MEMBERS",
    "HOUR_APPR_PROCESS_START"
]

CATEGORICAL_COLUMNS = [
    "FLAG_OWN_CAR",
    "FLAG_OWN_REALTY",
    "NAME_INCOME_TYPE",
    "NAME_EDUCATION_TYPE",
    "NAME_HOUSING_TYPE",
    "WEEKDAY_APPR_PROCESS_START",
]

FEATURE_COLUMNS = NUMERIC_COLUMNS + CATEGORICAL_COLUMNS

ANOMALY_COLUMNS = [
    "AMT_INCOME_TOTAL",
    "AMT_CREDIT",
    "AMT_ANNUITY",
    "AMT_GOODS_PRICE",
    "DAYS_EMPLOYED",
    "DAYS_REGISTRATION"
]


def train_and_save():
    config.secret("UW_ARTIFACT_KEY")

    dataset_path = config.HOME_CREDIT_TRAIN_PATH

    if not os.path.isfile(dataset_path):
        raise FileNotFoundError(
            f"Home Credit training file not found: {dataset_path}"
        )

    print("Loading Home Credit training dataset...")

    df = pd.read_csv(dataset_path)

    required_columns = FEATURE_COLUMNS + ["TARGET"]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Home Credit dataset is missing columns: "
            + ", ".join(missing_columns)
        )

    if "SK_ID_CURR" not in df.columns:
        raise ValueError("SK_ID_CURR column is missing.")

    df = df.copy()

    df["TARGET"] = pd.to_numeric(
        df["TARGET"],
        errors="coerce"
    )

    df = df.dropna(subset=["TARGET"])

    if not df["TARGET"].isin([0, 1]).all():
        raise ValueError("TARGET must contain only 0 and 1.")

    df["DAYS_EMPLOYED"] = pd.to_numeric(
        df["DAYS_EMPLOYED"],
        errors="coerce"
    )

    df.loc[
        df["DAYS_EMPLOYED"] == 365243,
        "DAYS_EMPLOYED"
    ] = np.nan

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    for column in CATEGORICAL_COLUMNS:
        df[column] = df[column].astype(object)
        df[column] = df[column].where(
            df[column].notna(),
            np.nan
        )

    df[FEATURE_COLUMNS] = df[FEATURE_COLUMNS].replace(
        [np.inf, -np.inf],
        np.nan
    )

    X = df[FEATURE_COLUMNS].copy()
    y = df["TARGET"].astype(int)

    class_counts = y.value_counts()

    if len(class_counts) != 2:
        raise ValueError(
            "Training requires both default and non-default records."
        )

    if class_counts.min() < 2:
        raise ValueError(
            "Not enough examples in the minority class for stratified training."
        )

    print("\nDataset distribution:")
    print(y.value_counts().sort_index())

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y
    )

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median"))
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="constant",
                    fill_value="Unknown"
                )
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True
                )
            )
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_transformer,
                NUMERIC_COLUMNS
            ),
            (
                "categorical",
                categorical_transformer,
                CATEGORICAL_COLUMNS
            )
        ],
        remainder="drop"
    )

    print("\nPreprocessing training features...")

    X_train_transformed = preprocessor.fit_transform(X_train)
    X_test_transformed = preprocessor.transform(X_test)

    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())

    scale_pos_weight = negative_count / positive_count

    print("Training XGBoost model...")

    xgb_model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="aucpr",
        objective="binary:logistic",
        tree_method="hist",
        n_jobs=-1
    )

    xgb_model.fit(
        X_train_transformed,
        y_train
    )

    y_probabilities = xgb_model.predict_proba(
        X_test_transformed
    )[:, 1]

    y_predictions = (y_probabilities >= 0.45).astype(int)

    print("\nModel Evaluation")
    print("-" * 50)

    print(
        "ROC-AUC:",
        round(
            roc_auc_score(y_test, y_probabilities),
            4
        )
    )

    print(
        "PR-AUC:",
        round(
            average_precision_score(y_test, y_probabilities),
            4
        )
    )

    print("\nClassification Report:")

    print(
        classification_report(
            y_test,
            y_predictions,
            labels=[0, 1],
            target_names=["Non-Default", "Default"],
            zero_division=0
        )
    )

    print("Training Isolation Forest...")

    anomaly_preprocessor = SimpleImputer(
        strategy="median"
    )

    X_anomaly_train = anomaly_preprocessor.fit_transform(
        X_train[ANOMALY_COLUMNS]
    )

    isolation_forest = IsolationForest(
        n_estimators=150,
        contamination=0.05,
        random_state=42,
        n_jobs=-1
    )

    isolation_forest.fit(X_anomaly_train)

    isolation_pipeline = Pipeline(
        steps=[
            ("imputer", anomaly_preprocessor),
            ("isolation_forest", isolation_forest)
        ]
    )

    print("Creating SHAP explainer...")

    explainer = shap.TreeExplainer(xgb_model)

    transformed_feature_names = preprocessor.get_feature_names_out().tolist()

    artifacts = {
        "model": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", xgb_model)
            ]
        ),
        "isolation_forest": isolation_pipeline,
        "explainer": explainer,
        "feature_names": FEATURE_COLUMNS,
        "anomaly_columns": ANOMALY_COLUMNS,
        "transformed_feature_names": transformed_feature_names,
        "dataset_name": "Home Credit Default Risk",
        "target_column": "TARGET",
        "decision_threshold": 0.45
    }

    artifact_directory = os.path.dirname(
        os.path.abspath(config.ARTIFACT_PATH)
    )

    os.makedirs(
        artifact_directory,
        exist_ok=True
    )

    temporary_path = config.ARTIFACT_PATH + ".tmp"

    try:
        joblib.dump(
            artifacts,
            temporary_path
        )

        try:
            os.chmod(temporary_path, 0o600)
        except OSError:
            pass

        os.replace(
            temporary_path,
            config.ARTIFACT_PATH
        )

        try:
            os.chmod(config.ARTIFACT_PATH, 0o600)
        except OSError:
            pass

        write_signature(config.ARTIFACT_PATH)

    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

    print("\nTraining completed successfully.")
    print("Dataset: Home Credit Default Risk")
    print("Total records:", len(df))
    print("Training records:", len(X_train))
    print("Testing records:", len(X_test))
    print("Default records:", int(y.sum()))
    print("Non-default records:", int((y == 0).sum()))
    print("Model artifacts saved and signed.")


if __name__ == "__main__":
    train_and_save()
