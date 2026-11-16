
import numpy as np
import pandas as pd


class FairnessAgent:

    def __init__(
        self,
        model,
        feature_names: list,
        threshold: float = 0.80,
        approval_score: float = 60.0
    ):
        self.model = model
        self.feature_names = feature_names
        self.dir_threshold = threshold
        self.approval_score = approval_score

    def _predict_approvals(self, df):
        missing = [
            column for column in self.feature_names
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing model features in fairness dataset: {missing}"
            )

        protected_features = {
            "CODE_GENDER",
            "DAYS_BIRTH",
            "gender",
            "age_group"
        }

        leakage = protected_features.intersection(self.feature_names)

        if leakage:
            raise ValueError(
                f"Protected attributes must not be model features: {sorted(leakage)}"
            )

        features = df[self.feature_names].copy()
        probabilities = self.model.predict_proba(features)[:, 1]

        if not np.isfinite(probabilities).all():
            raise ValueError("Model returned invalid probabilities.")

        risk_scores = (1.0 - probabilities) * 100

        return (risk_scores >= self.approval_score).astype(int)

    def _group_metrics(self, df, protected_col, privileged_group):
        valid = df[
            df[protected_col].notna()
        ].copy()

        grouped = valid.groupby(
            protected_col,
            observed=True
        )["approved"].agg(["mean", "count", "sum"])

        if privileged_group not in grouped.index:
            return {
                "reference_group": privileged_group,
                "status": "Reference group unavailable",
                "groups": {}
            }

        reference_rate = float(
            grouped.loc[privileged_group, "mean"]
        )

        metrics = {}

        for group, row in grouped.iterrows():
            approval_rate = float(row["mean"])

            dir_score = (
                approval_rate / reference_rate
                if reference_rate > 0 else None
            )

            dp_difference = abs(
                approval_rate - reference_rate
            )

            metrics[str(group)] = {
                "sample_count": int(row["count"]),
                "approved_count": int(row["sum"]),
                "approval_rate": round(approval_rate, 4),
                "disparate_impact_ratio": (
                    round(dir_score, 4)
                    if dir_score is not None else None
                ),
                "demographic_parity_difference": round(
                    dp_difference, 4
                ),
                "passes_80_percent_rule": (
                    bool(dir_score >= self.dir_threshold)
                    if dir_score is not None else None
                )
            }

        return {
            "reference_group": str(privileged_group),
            "reference_approval_rate": round(reference_rate, 4),
            "status": "Calculated",
            "groups": metrics
        }

    def audit_home_credit(self, df):
        required = ["CODE_GENDER", "DAYS_BIRTH"]

        missing = [
            column for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing protected attributes: {missing}"
            )

        if df.empty:
            raise ValueError("Fairness dataset is empty.")

        if self.feature_names and any(
            column in {"CODE_GENDER", "DAYS_BIRTH"}
            for column in self.feature_names
        ):
            raise ValueError(
                "Protected attributes must be excluded from model features."
            )

        results = df.copy()
        results["approved"] = self._predict_approvals(results)

        gender = (
            results["CODE_GENDER"]
            .astype("string")
            .str.strip()
            .str.upper()
        )

        results["gender_group"] = gender.where(
            gender.isin(["M", "F"]),
            pd.NA
        )

        birth_days = pd.to_numeric(
            results["DAYS_BIRTH"],
            errors="coerce"
        )

        age = birth_days.abs() / 365.25

        results["age_group"] = pd.cut(
            age,
            bins=[0, 25, 50, np.inf],
            labels=["UNDER_25", "25_50", "OVER_50"],
            right=False
        )

        gender_audit = self._group_metrics(
            results,
            "gender_group",
            "M"
        )

        age_audit = self._group_metrics(
            results,
            "age_group",
            "25_50"
        )

        return {
            "dataset": "Home Credit application_test.csv",
            "evaluation_type": "Unlabelled holdout selection-rate audit",
            "approval_definition": (
                f"credit_risk_score >= {self.approval_score}"
            ),
            "total_records": int(len(results)),
            "approved_records": int(results["approved"].sum()),
            "overall_approval_rate": round(
                float(results["approved"].mean()), 4
            ),
            "gender_unknown_records": int(
                results["gender_group"].isna().sum()
            ),
            "age_unknown_records": int(
                results["age_group"].isna().sum()
            ),
            "gender_fairness": gender_audit,
            "age_fairness": age_audit,
            "limitations": [
                "Home Credit application_test has no default outcome labels.",
                "This audit measures demographic parity in model selections only.",
                "The 80 percent rule is a screening indicator, not proof of fairness.",
                "Review group sizes, confidence intervals and intersectional groups."
            ]
        }

    def audit(self, df):
        if {
            "CODE_GENDER",
            "DAYS_BIRTH"
        }.issubset(df.columns):
            return self.audit_home_credit(df)

        required = {
            "consent_given",
            "gender",
            "age_group"
        }

        if not required.issubset(df.columns):
            raise ValueError(
                "Dataset does not match either supported fairness schema."
            )

        consented = df[
            df["consent_given"].fillna(False).astype(bool)
        ].copy()

        if consented.empty:
            raise ValueError("No consented records available for audit.")

        consented["approved"] = self._predict_approvals(
            consented
        )

        return {
            "dataset": "Consent-controlled applicant dataset",
            "approval_definition": (
                f"credit_risk_score >= {self.approval_score}"
            ),
            "total_records": int(len(consented)),
            "gender_fairness": self._group_metrics(
                consented, "gender", "Male"
            ),
            "age_fairness": self._group_metrics(
                consented, "age_group", "25_50"
            )
        }
