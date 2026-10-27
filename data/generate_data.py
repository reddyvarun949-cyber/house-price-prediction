"""Generate the synthetic house price dataset used in this project.

Run from the project root:  python data/generate_data.py
The output is data/house_prices.csv. The seed is fixed, so everyone gets the same file.

The prices follow a realistic pattern (bigger, newer, closer to the metro and in a premium
locality = more expensive) plus random noise. A few rows are made messy on purpose
(missing values, duplicates) so the notebook can show how to clean them.
"""
import os

import numpy as np
import pandas as pd

SEED = 42
N = 1500

# locality name -> price per square foot in rupees (fictional city)
LOCALITIES = {
    "Green Park": 9500, "Lake View": 8200, "Old Town": 5200, "Tech City": 7800,
    "Riverside": 6900, "Hill Top": 6100, "Market Area": 5800, "New Colony": 4700,
}


def make_dataset(n=N, seed=SEED):
    rng = np.random.default_rng(seed)
    locality = rng.choice(list(LOCALITIES), size=n, p=[0.1, 0.12, 0.14, 0.16, 0.12, 0.12, 0.12, 0.12])
    bedrooms = rng.choice([1, 2, 3, 4, 5], size=n, p=[0.12, 0.38, 0.32, 0.14, 0.04])
    area = (bedrooms * 420 + rng.normal(250, 160, n)).clip(350, 4200).round(0)
    bathrooms = np.minimum(bedrooms + rng.choice([-1, 0, 0, 1], size=n), 5).clip(1)
    age = rng.integers(0, 36, n)
    metro = rng.gamma(2.0, 1.6, n).clip(0.2, 15).round(1)
    floor = rng.integers(0, 21, n)
    parking = rng.choice(["Yes", "No"], size=n, p=[0.7, 0.3])
    furnishing = rng.choice(["Unfurnished", "Semi-Furnished", "Fully-Furnished"], size=n, p=[0.35, 0.45, 0.2])

    rate = np.array([LOCALITIES[l] for l in locality])
    price_rupees = (
        area * rate
        * (1 - 0.009 * age)                    # older homes are cheaper
        * (1 - 0.025 * np.minimum(metro, 10))  # far from metro is cheaper
        * np.where(parking == "Yes", 1.06, 1.0)
        * pd.Series(furnishing).map({"Unfurnished": 1.0, "Semi-Furnished": 1.05, "Fully-Furnished": 1.12}).to_numpy()
        * (1 + 0.004 * np.minimum(floor, 12))
        + bathrooms * 150000
    )
    price_rupees *= rng.normal(1.0, 0.08, n)      # market noise
    price_lakhs = (price_rupees / 100000).round(2)

    df = pd.DataFrame({
        "house_id": np.arange(1, n + 1),
        "locality": locality, "area_sqft": area, "bedrooms": bedrooms, "bathrooms": bathrooms,
        "age_years": age, "distance_to_metro_km": metro, "floor": floor,
        "parking": parking, "furnishing": furnishing, "price_lakhs": price_lakhs,
    })

    # realistic messiness
    for col, k in (("area_sqft", 12), ("age_years", 20), ("furnishing", 15), ("distance_to_metro_km", 10)):
        idx = rng.choice(n, size=k, replace=False)
        df[col] = df[col].astype("object") if col == "furnishing" else df[col].astype("float")
        df.loc[idx, col] = np.nan
    dupes = df.sample(25, random_state=seed)
    df = pd.concat([df, dupes], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)
    return df


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "house_prices.csv")
    data = make_dataset()
    data.to_csv(out, index=False)
    print(f"Wrote {len(data)} rows to {out}")
