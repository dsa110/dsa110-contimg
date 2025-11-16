# Document Inventory - Start Here

Welcome! This is your complete guide to the 630-document inventory for the
DSA-110 Continuum Imaging Pipeline.

## What Was Done

All documents in `/data/dsa110-contimg/docs/` (and subdirectories) have been
scanned and categorized by theme. Each document is now tagged with:

- **Pipeline Stage(s)** - Which stage(s) of the imaging pipeline it relates to
- **Dashboard Component(s)** - Which part(s) of the dashboard it relates to
- **General Theme(s)** - Development, testing, operations, etc.
- **Modification Date** - When it was last updated

## Files Available

### For Spreadsheet Work (CSV Format)

**Recommended: `DOCUMENT_INVENTORY_SUMMARY.csv`**

- Clean, simple three-column format
- Perfect for Excel, Google Sheets, or LibreOffice
- Contains: Document Name | Themes | Last Modified
- All 630 documents in rows

**Detailed: `DOCUMENT_INVENTORY_ANALYSIS.csv`**

- Full path information included
- Contains: filename | path | themes | date_modified
- Better for scripting and advanced analysis

**Pivot View: `DOCUMENT_INVENTORY_BY_THEME.csv`**

- Organized by theme category
- Shows count of documents per theme
- Lists sample documents in each theme

### For Reading (Markdown & Text)

**`DOCUMENT_INVENTORY_REPORT.md`** - Comprehensive Analysis

- Executive summary with statistics
- Tables showing coverage by pipeline stage
- Tables showing coverage by dashboard component
- Key observations and insights
- Theme distribution analysis

**`QUICK_REFERENCE_DOCUMENT_FINDER.md`** - Quick Lookup Guide

- Documents organized by each pipeline stage
- Documents organized by each dashboard component
- Documents organized by general theme
- Quick reference statistics

**`THEME_IDENTIFICATION_SUMMARY.txt`** - Technical Details

- Methodology explanation
- Complete theme breakdown
- Usage guidelines
- Key findings

## Quick Navigation

### Looking for Pipeline Documentation?

**Pipeline Stages** (10 total, 132 documents):

1. **Streaming** (13 docs) - Data ingestion, UVH5 conversion
2. **Calibration** (12 docs) - Calibration procedures
3. **Flagging** (2 docs) - RFI detection
4. **Imaging** (22 docs) - Image generation
5. **Masking** (5 docs) - Image masking
6. **Mosaicing** (17 docs) - Mosaic building
7. **QA** (25 docs) - Quality assurance
8. **Cross-Matching** (29 docs) - Source identification
9. **Photometry** (8 docs) - Flux measurement
10. **ESE Detection** (26 docs) - Error detection

→ Use `QUICK_REFERENCE_DOCUMENT_FINDER.md` to find docs for a specific stage

### Looking for Dashboard Documentation?

**Dashboard Components** (6 total, 195 documents):

1. **Frontend** (89 docs) - React UI, pages, templates
2. **Visualization** (40 docs) - JS9, CARTA, charts
3. **Architecture** (32 docs) - Design patterns, data flow
4. **Backend** (22 docs) - API endpoints, database
5. **Monitoring** (8 docs) - System health, pointing
6. **Control Panel** (4 docs) - Operations interface

→ Use `QUICK_REFERENCE_DOCUMENT_FINDER.md` to find docs for a specific component

### Looking by Topic?

**General Themes** (11 categories):

| Theme           | Docs | Purpose                     |
| --------------- | ---- | --------------------------- |
| Testing         | 104  | Test strategies and results |
| Development     | 103  | Implementation roadmaps     |
| Documentation   | 67   | Guides and references       |
| Troubleshooting | 56   | Bug fixes and solutions     |
| Operations      | 32   | Deployment and maintenance  |
| Tools           | 26   | Tool evaluation             |
| Environment     | 20   | Setup and configuration     |
| Deployment      | 18   | Docker and systemd          |
| Performance     | 11   | Optimization                |
| Security        | 9    | Safeguards                  |
| Miscellaneous   | 126  | Administrative              |

→ Use `DOCUMENT_INVENTORY_BY_THEME.csv` or `QUICK_REFERENCE_DOCUMENT_FINDER.md`

## How to Use the CSVs

### In Excel or Google Sheets:

1. Open `DOCUMENT_INVENTORY_SUMMARY.csv`
2. Use the filter dropdowns to find documents:
   - Filter by "Themes" to find all docs with a specific tag
   - Filter by "Last Modified" to find recent updates
3. Sort by any column to organize your view

### For Custom Analysis:

1. Use `DOCUMENT_INVENTORY_ANALYSIS.csv` for full path information
2. Import into Python/R for programmatic analysis:
   ```python
   import pandas as pd
   df = pd.read_csv('DOCUMENT_INVENTORY_ANALYSIS.csv')
   # Filter by theme
   qa_docs = df[df['themes'].str.contains('pipeline: qa')]
   ```

### For Theme-Based Discovery:

1. Open `DOCUMENT_INVENTORY_BY_THEME.csv`
2. Find your theme of interest
3. See sample documents and count
4. Open those documents for more details

## Key Statistics

| Metric                  | Value     |
| ----------------------- | --------- |
| Total Documents         | 630       |
| Pipeline Documents      | 132 (21%) |
| Dashboard Documents     | 195 (31%) |
| Testing Documents       | 104 (17%) |
| Development Documents   | 103 (16%) |
| Docs Modified Nov 13-14 | 343 (54%) |

## Example Queries

**"How do I use CASA?"** → Search for "CASA" or filter for theme "pipeline:
imaging" and "environment"

**"What's new in dashboard frontend?"** → Filter for theme "dashboard: frontend"
and sort by "Last Modified"

**"What are the calibration procedures?"** → Filter for theme "pipeline:
calibration"

**"Where's the control panel documentation?"** → Filter for theme "dashboard:
control"

**"How do I run tests?"** → Filter for theme "testing"

**"What deployment options are available?"** → Filter for theme "deployment"

## Document Organization

The documents are organized by directory:

```
/data/dsa110-contimg/docs/
├── how-to/           - Procedural guides
├── reference/        - API and technical references
├── concepts/         - Architecture and design
├── operations/       - Deployment and operations
├── dev/              - Development status and tracking
├── archive/          - Historical and superseded docs
├── testing/          - Testing strategies and results
├── tutorials/        - Step-by-step tutorials
└── [root]            - Main documents
```

## Notes

- Many documents have **multiple themes** because they address multiple concerns
  - Example: "QA_VISUALIZATION_DESIGN.md" is tagged as:
    - `pipeline: qa`
    - `dashboard: visualization`
    - `dashboard: architecture`

- **Archives** contain historical documentation
  - If a document appears in both `archive/` and root, the root version is
    current

- **Dates** reflect file modification times as logged on the system
  - Most documents (97.5%) were updated Nov 12-14, 2025

## Getting Help

1. **For a specific document**: Check `DOCUMENT_INVENTORY_SUMMARY.csv`
2. **For documents on a topic**: Use filters in the CSV
3. **For context**: Read `DOCUMENT_INVENTORY_REPORT.md`
4. **For quick lookup**: Check `QUICK_REFERENCE_DOCUMENT_FINDER.md`
5. **For technical details**: Read `THEME_IDENTIFICATION_SUMMARY.txt`

---

**All inventory files are in `/data/dsa110-contimg/docs/`**

Start with `DOCUMENT_INVENTORY_SUMMARY.csv` for the easiest experience!
