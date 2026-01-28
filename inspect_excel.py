import pandas as pd

file_path = "/Users/mike/Documents/running/2026/swimming-program/RottoTraining MARLENE New New.xlsx"

try:
    xls = pd.ExcelFile(file_path)
    print("Sheet names:", xls.sheet_names)
except Exception as e:
    print(f"Error reading Excel file: {e}")
