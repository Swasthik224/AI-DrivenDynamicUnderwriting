import pandas as pd

import config
from security import load_verified_artifacts

APPROVAL_THRESHOLD = 0.45
GENDER_REFERENCE_GROUP = "Male"
AGE_REFERENCE_GROUP = "25_50"


def consent_mask(series):
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )


def calculate_dir(dataframe, attribute, privileged_group):
    valid_data = dataframe.dropna(subset=[attribute]).copy()

    if valid_data.empty:
        return {
            "reference_group": privileged_group,
            "reference_group_found": False,
            "groups": {}
        }

    grouped = valid_data.groupby(attribute, observed=True)["approved"].agg(
        approval_rate="mean",
        sample_count="count",
        approval_count="sum"
    )

    reference_key = str(privileged_group)

    reference_rate = None

    for group in grouped.index:
        if str(group) == reference_key:
            reference_rate = float(grouped.loc[group, "approval_rate"])
            break

    reference_found = reference_rate is not None
    results = {}

    for group, row in grouped.iterrows():
        rate = float(row["approval_rate"])

        if not reference_found or reference_rate == 0:
            dir_value = None
            compliant = None
        else:
            dir_value = rate / reference_rate
            compliant = bool(dir_value >= 0.80)

        results[str(group)] = {
            "approval_rate": round(rate, 4),
            "disparate_impact_ratio": (
                round(float(dir_value), 4)
                if dir_value is not None
                else None
            ),
            "is_80_percent_compliant": compliant,
            "sample_count": int(row["sample_count"]),
            "approval_count": int(row["approval_count"])
        }

    return {
        "reference_group": privileged_group,
        "reference_group_found": reference_found,
        "groups": results
    }


def run_fairness_audit():
    artifacts = load_verified_artifacts(config.ARTIFACT_PATH)

    model = artifacts["model"]
    feature_names = artifacts["feature_names"]

    df = pd.read_csv(config.DATASET_PATH)

    required_columns = (
            list(feature_names)
            + [
                "consent_given",
                "gender",
                "age_group"
            ]
    )

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    df = df.copy()
    df["consent_given"] = consent_mask(df["consent_given"])
    df_consented = df.loc[df["consent_given"]].copy()

    if df_consented.empty:
        raise ValueError(
            "Fairness audit cannot run because there are no consented records."
        )

    df_consented[feature_names] = df_consented[feature_names].apply(
        pd.to_numeric,
        errors="coerce"
    )

    if df_consented[feature_names].isnull().any().any():
        raise ValueError(
            "Consented records contain missing or invalid model feature values."
        )

    probabilities = model.predict_proba(
        df_consented[feature_names]
    )[:, 1]

    df_consented["approved"] = (
            probabilities < APPROVAL_THRESHOLD
    ).astype(int)

    results = {
        "consented_records": int(len(df_consented)),
        "approval_threshold": APPROVAL_THRESHOLD,
        "approval_definition": (
            f"default_probability < {APPROVAL_THRESHOLD}"
        ),
        "gender_audit": calculate_dir(
            df_consented,
            "gender",
            GENDER_REFERENCE_GROUP
        ),
        "age_audit": calculate_dir(
            df_consented,
            "age_group",
            AGE_REFERENCE_GROUP
        )
    }

    print("=" * 65)
    print("FAIRNESS AND DISPARATE IMPACT AUDIT REPORT")
    print("=" * 65)
    print(f"Consented records analysed: {results['consented_records']}")
    print(f"Approval definition: {results['approval_definition']}")

    for audit_name, audit in (
            ("Gender", results["gender_audit"]),
            ("Age Group", results["age_audit"])
    ):
        print(f"\n[{audit_name} Analysis]")
        print(f"Reference group: {audit['reference_group']}")

        if not audit["reference_group_found"]:
            print("Reference group not found. DIR cannot be calculated.")

        for group, metrics in audit["groups"].items():
            rate = metrics["approval_rate"]
            ratio = metrics["disparate_impact_ratio"]
            compliant = metrics["is_80_percent_compliant"]

            ratio_text = (
                f"{ratio:.3f}" if ratio is not None else "N/A"
            )

            if compliant is None:
                status = "NOT EVALUATED"
            else:
                status = "PASSED" if compliant else "FAILED"

            print(
                f"  {group:15s} | "
                f"Approval Rate: {rate:.2%} | "
                f"DIR: {ratio_text} | "
                f"Samples: {metrics['sample_count']} | "
                f"Approvals: {metrics['approval_count']} | "
                f"{status}"
            )

    return results


if __name__ == "__main__":
    run_fairness_audit()
