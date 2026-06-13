# XLSX Tabs to CSV

Interactive Python utility that exports every worksheet/tab from an XLSX workbook into separate CSV files and creates an `_index.csv`.

## Install

pip install openpyxl

## Run Interactive Mode

python xlsx_tabs_to_csv.py

The script will ask for:

1. XLSX file path
2. Output folder
3. Whether to overwrite existing exports

## Run Direct Mode

python xlsx_tabs_to_csv.py "C:\path\to\file.xlsx"

## Run Direct Mode With Output Folder

python xlsx_tabs_to_csv.py "C:\path\to\file.xlsx" --out "C:\path\to\export_folder"

## Overwrite Existing Output

python xlsx_tabs_to_csv.py "C:\path\to\file.xlsx" --out "C:\path\to\export_folder" --overwrite

## Output

The export folder will contain one CSV per worksheet and an `_index.csv` file.

Example:

my_file_csv_export/
  Sheet1.csv
  Sheet2.csv
  Transactions.csv
  _index.csv