import pandas as pd

file_path = "/Users/mike/Documents/running/2026/swimming-program/RottoTraining MARLENE New New.xlsx"
sheet_name = "Program"

try:
    # Read the first 20 rows to get an idea of the structure
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=20)

    # Print the DataFrame to inspect
    print(df.to_string())
except Exception as e:
    print(f"Error reading sheet '{sheet_name}': {e}")
