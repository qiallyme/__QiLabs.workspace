# CSV to Markdown Converter - Usage Guide

## Quick Start

### Basic Usage (with config file)

```powershell
# Activate virtual environment
& "c:/Users/codyr/My Drive/QiOne/.venv/Scripts/Activate.ps1"

# Run conversion
python csv_to_md.py --csv "data/You Thought That You Knew Me-all.csv" --out "./output" --config "mapping.json"
```

### Without Config (Interactive Mode)

If you don't have a config file, the script will prompt you interactively:

```powershell
python csv_to_md.py --csv "path/to/your/file.csv" --out "./output"
```

**Note:** Interactive mode requires a terminal that supports input. If you get `EOFError`, use `--config` instead.

## Command Line Options

- `--csv` (required): Path to input CSV file
- `--out` (required): Output directory for generated .md files
- `--config` (optional): JSON file with column mapping configuration
- `--filename_from` (optional): Use "title" or "slug" for filenames (default: "title")
- `--no_json_dump` (optional): Disable raw JSON dump in footnotes

## Config File Format

Create a `mapping.json` file like this:

```json
{
  "title": "Title",
  "date": "Created",
  "tags": "Labels",
  "qicode": "QiCode",
  "summary": "Summary",
  "content_cols": ["Body", "Notes"]
}
```

### Mapping Keys

- `title`: Column name for the page title
- `slug`: Column name for URL-friendly slug (optional, auto-generated from title if missing)
- `date`: Column name for date field
- `tags`: Column name for tags (comma/semicolon separated)
- `qicode`: Column name for QiCode ID
- `status`: Column name for status field
- `category`: Column name for category
- `summary`: Column name for summary/description
- `content_cols`: Array of column names to use as page content (in order)

## Example CSV Structure

Your CSV should have headers that match your mapping:

```csv
Title,Created,Labels,QiCode,Summary,Body,Notes
"My First Note",2025-11-04,"#client, intake","QICODE-001","Brief summary","Main content here","Additional notes"
```

## Output

- Each CSV row becomes one Markdown file
- Filename is generated from title (slugified)
- YAML front matter includes all mapped fields
- Unmapped columns appear in "Footnotes / Source Data" section
- Raw JSON is included in a collapsible details section

## Troubleshooting

### FileNotFoundError

Make sure your CSV path is correct. Use relative paths from the script directory or absolute paths:

```powershell
# Relative path (from csv-to-md directory)
python csv_to_md.py --csv "data/myfile.csv" --out "./output"

# Absolute path
python csv_to_md.py --csv "C:\Users\codyr\My Drive\QiOne\path\to\file.csv" --out "C:\Users\codyr\My Drive\QiOne\output"
```

### EOFError in Interactive Mode

Use `--config` flag instead:

```powershell
python csv_to_md.py --csv "data/file.csv" --out "./output" --config "mapping.json"
```

### No Output Files

- Check that the CSV has data rows (not just headers)
- Verify output directory path is correct
- Check file permissions

## Current Mapping

The current `mapping.json` maps:
- **Title** → `title`
- **Created** → `date`
- **Labels** → `tags`
- **QiCode** → `qicode`
- **Summary** → `summary`
- **Body, Notes** → `content_cols` (page content)

## Files Generated

✅ **128 files** generated from "You Thought That You Knew Me-all.csv"
📁 Output location: `output/` directory

