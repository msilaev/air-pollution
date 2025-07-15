import pandas as pd

from src.config import USE_S3
from src.data.data_loader import DataLoader

# Load data to check feature names
data_loader = DataLoader(use_s3=USE_S3)
df = data_loader.load_predicting_dataset()

print("Dataset shape:", df.shape)
print("\nColumn names:")
for col in df.columns:
    print(f"  {col}")

print("\nPollution columns (containing 'matter' or 'Nitrogen'):")
pollution_cols = [col for col in df.columns if ("matter" in col or "Nitrogen" in col)]
for col in pollution_cols:
    print(f"  {col}")
