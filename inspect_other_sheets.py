import pandas as pd

file_path = "/Users/mike/Documents/running/2026/swimming-program/RottoTraining MARLENE New New.xlsx"
sheet_name = "Swim Splits"

try:
    # Read the first 50 rows of "Swim Splits"
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=50)
    print(f"--- Sheet: {sheet_name} ---")
    print(df.fillna("").to_string())
except Exception as e:
    print(f"Error reading sheet '{sheet_name}': {e}")
