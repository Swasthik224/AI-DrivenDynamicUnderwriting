"""
generate_dataset.py
-------------------
Generates synthetic data using the SAME feature set the API/dashboard actually
send, so the trained model responds to every signal exposed in the UI.
"""

import numpy as np
import pandas as pd


def generate_underwriting_data(num_samples: int = 2000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)

    genders = np.random.choice(["Male", "Female", "Non-Binary"], size=num_samples, p=[0.49, 0.49, 0.02])
    age_groups = np.random.choice(["Under_25", "25_50", "Over_50"], size=num_samples, p=[0.25, 0.60, 0.15])
    consent_given = np.random.choice([True, False], size=num_samples, p=[0.92, 0.08])

    # Traditional signals
    traditional_score = np.random.normal(650, 80, num_samples).clip(300, 850)
    monthly_income_inr = np.random.lognormal(10.5, 0.6, num_samples).clip(15000, 500000)
    debt_to_income_ratio = np.random.beta(2, 5, num_samples).clip(0.05, 0.85)
    num_existing_loans = np.random.poisson(1.5, num_samples).clip(0, 8)

    # Alternative / behavioral signals — MUST match FullApplicantSchema in app.py
    upi_monthly_tx_volume = np.random.negative_binomial(8, 0.15, num_samples).clip(2, 200)
    bnpl_repayment_rate = np.random.beta(7, 2, num_samples)
    utility_pay_punctuality = np.random.beta(7, 2, num_samples)
    telecom_recharge_regularity = np.random.beta(6, 2, num_samples)
    ecommerce_monthly_spend = (monthly_income_inr * np.random.uniform(0.05, 0.30, num_samples)).clip(500, 50000)
    ecommerce_return_rate = np.random.beta(2, 12, num_samples)
    gig_income_stability_index = np.random.beta(5, 3, num_samples)
    digital_footprint_consistency = np.random.beta(8, 2, num_samples)
    device_change_frequency = np.random.poisson(0.8, num_samples).clip(0, 8)
    mobile_wallet_tx_freq = np.random.negative_binomial(5, 0.1, num_samples).clip(2, 150)

    # Latent default risk — every alt-data signal actually contributes
    z = (
        - 0.008 * (traditional_score - 600)
        - 0.00002 * (monthly_income_inr - 30000)
        + 3.2 * debt_to_income_ratio
        + 0.35 * num_existing_loans
        - 1.8 * bnpl_repayment_rate
        - 1.6 * utility_pay_punctuality
        - 1.2 * telecom_recharge_regularity
        - 1.8 * gig_income_stability_index
        - 1.4 * digital_footprint_consistency
        + 2.0 * ecommerce_return_rate
        + 0.15 * device_change_frequency
        - 0.004 * (upi_monthly_tx_volume - 40)
        + np.random.normal(0, 0.8, num_samples)
    )

    default_prob = 1 / (1 + np.exp(-z))
    default_flag = (default_prob > 0.45).astype(int)

    df = pd.DataFrame({
        "applicant_id": [f"APP_{1000+i}" for i in range(num_samples)],
        "gender": genders,
        "age_group": age_groups,
        "consent_given": consent_given,
        "traditional_score": np.round(traditional_score, 0),
        "monthly_income_inr": np.round(monthly_income_inr, 2),
        "debt_to_income_ratio": np.round(debt_to_income_ratio, 3),
        "num_existing_loans": num_existing_loans,
        "upi_monthly_tx_volume": upi_monthly_tx_volume,
        "bnpl_repayment_rate": np.round(bnpl_repayment_rate, 3),
        "utility_pay_punctuality": np.round(utility_pay_punctuality, 3),
        "telecom_recharge_regularity": np.round(telecom_recharge_regularity, 3),
        "ecommerce_monthly_spend": np.round(ecommerce_monthly_spend, 2),
        "ecommerce_return_rate": np.round(ecommerce_return_rate, 3),
        "gig_income_stability_index": np.round(gig_income_stability_index, 3),
        "digital_footprint_consistency": np.round(digital_footprint_consistency, 3),
        "device_change_frequency": device_change_frequency,
        "mobile_wallet_tx_freq": mobile_wallet_tx_freq,
        "default_flag": default_flag
    })

    return df


if __name__ == "__main__":
    dataset = generate_underwriting_data(num_samples=2000)
    dataset.to_csv("underwriting_dataset.csv", index=False)
    print(f"Dataset generated with {len(dataset)} records.")
    print(f"Default Rate: {dataset['default_flag'].mean():.2%}")
    print(dataset.head(3))