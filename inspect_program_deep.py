import pandas as pd

file_path = "/Users/mike/Documents/running/2026/swimming-program/RottoTraining MARLENE New New.xlsx"
sheet_name = "Program"

try:
    # Read the first 50 rows
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=50)

    # Fill NaN with empty string for better readability
    df_filled = df.fillna("")

    # Print the DataFrame shape
    print(f"Shape: {df.shape}")

    # Print the first 50 rows
    print(df_filled.to_string())
except Exception as e:
    print(f"Error reading sheet '{sheet_name}': {e}")
