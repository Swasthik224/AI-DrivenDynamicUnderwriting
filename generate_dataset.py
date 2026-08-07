"""
generate_dataset.py
-------------------
Generates a realistic synthetic dataset combining traditional credit metrics
and alternative financial/digital footprint data for underwriting.
"""

import numpy as np
import pandas as pd


def generate_underwriting_data(num_samples: int = 1000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)

    # 1. Demographic Metadata (for Bias Audit)
    genders = np.random.choice(["Male", "Female", "Non-Binary"], size=num_samples, p=[0.49, 0.49, 0.02])
    age_groups = np.random.choice(["Under_25", "25_50", "Over_50"], size=num_samples, p=[0.25, 0.60, 0.15])
    consent_given = np.random.choice([True, False], size=num_samples, p=[0.92, 0.08])

    # 2. Traditional Financial Signals
    traditional_score = np.random.normal(loc=650, scale=80, size=num_samples).clip(300, 850)
    monthly_income_inr = np.random.lognormal(mean=10.5, sigma=0.6, size=num_samples).clip(15000, 500000)
    debt_to_income_ratio = np.random.beta(a=2, b=5, size=num_samples).clip(0.05, 0.85)
    num_existing_loans = np.random.poisson(lam=1.5, size=num_samples).clip(0, 8)

    # 3. Alternative Data Signals (Fintech / Digital Footprint)
    utility_pay_punctuality = np.random.beta(a=7, b=2, size=num_samples)  # 0.0 to 1.0
    ecommerce_monthly_spend = (monthly_income_inr * np.random.uniform(0.05, 0.30, num_samples)).clip(500, 50000)
    mobile_wallet_tx_freq = np.random.negative_binomial(n=5, p=0.1, size=num_samples).clip(2, 150)
    gig_income_stability_index = np.random.beta(a=5, b=3, size=num_samples)  # 0.0 to 1.0
    digital_footprint_consistency = np.random.beta(a=8, b=2, size=num_samples)  # Anomaly signal

    # 4. Generate Latent Default Risk & Target Variable
    # Higher income, utility punctuality, gig stability, and traditional score REDUCE default risk.
    # Higher debt-to-income and loan counts INCREASE default risk.
    z = (
            - 0.008 * (traditional_score - 600)
            - 0.00002 * (monthly_income_inr - 30000)
            + 3.5 * debt_to_income_ratio
            + 0.4 * num_existing_loans
            - 2.8 * utility_pay_punctuality
            - 2.2 * gig_income_stability_index
            - 1.5 * digital_footprint_consistency
            + np.random.normal(loc=0, scale=0.8, size=num_samples)
    )

    # Sigmoid function for default probability
    default_prob = 1 / (1 + np.exp(-z))
    default_flag = (default_prob > 0.45).astype(int)

    df = pd.DataFrame({
        "applicant_id": [f"APP_{1000 + i}" for i in range(num_samples)],
        "gender": genders,
        "age_group": age_groups,
        "consent_given": consent_given,
        "traditional_score": np.round(traditional_score, 0),
        "monthly_income_inr": np.round(monthly_income_inr, 2),
        "debt_to_income_ratio": np.round(debt_to_income_ratio, 3),
        "num_existing_loans": num_existing_loans,
        "utility_pay_punctuality": np.round(utility_pay_punctuality, 3),
        "ecommerce_monthly_spend": np.round(ecommerce_monthly_spend, 2),
        "mobile_wallet_tx_freq": mobile_wallet_tx_freq,
        "gig_income_stability_index": np.round(gig_income_stability_index, 3),
        "digital_footprint_consistency": np.round(digital_footprint_consistency, 3),
        "default_flag": default_flag
    })

    return df


if __name__ == "__main__":
    dataset = generate_underwriting_data(num_samples=1000)
    dataset.to_csv("underwriting_dataset.csv", index=False)
    print(f"Dataset generated successfully with {len(dataset)} records.")
    print(f"Default Rate: {dataset['default_flag'].mean():.2%}")
    print(dataset.head(3))