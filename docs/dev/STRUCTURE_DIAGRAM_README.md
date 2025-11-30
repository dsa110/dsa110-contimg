# Directory Structure Diagram Generator

A generalized script that automatically analyzes any directory structure and
generates a Mermaid flowchart diagram showing the organization and relationships
between modules.

## Usage

```bash
python scripts/generate_structure_diagram.py <directory_path> [output.svg]
```

### Examples

**Generate diagram for backend:**

```bash
python scripts/generate_structure_diagram.py /data/dsa110-contimg/backend docs/diagrams/backend_structure.svg
```

**Generate diagram for frontend:**

```bash
python scripts/generate_structure_diagram.py /data/dsa110-contimg/frontend docs/diagrams/frontend_structure.svg
```

**Generate diagram for any directory:**

```bash
python scripts/generate_structure_diagram.py /data/dsa110-contimg/docs docs/diagrams/docs_structure.svg
python scripts/generate_structure_diagram.py /data/dsa110-contimg/scripts docs/diagrams/scripts_structure.svg
```

## Features

- **Automatic Analysis**: Scans directory structure and identifies:

  - Python packages (directories with `__init__.py`)
  - Key configuration files
  - Test directories
  - Documentation directories
  - Script directories

- **Smart Organization**:

  - Groups related modules
  - Shows key files in each module
  - Identifies logical relationships

- **Relationship Detection**: Automatically detects common pipeline
  relationships:

  - `conversion :arrow_right: calibration :arrow_right: imaging :arrow_right: photometry :arrow_right: catalog`
  - `api :arrow_right: database`, `api :arrow_right: conversion`
  - `pipeline :arrow_right: conversion/calibration/imaging`
  - `utils :arrow_right: conversion/calibration/imaging`

- **Color Coding**: Different modules get different colors for easy
  identification

## Output Files

The script generates two files:

1. **`<output>.svg`** - Rendered SVG diagram (ready to use)
2. **`<output>.mmd`** - Mermaid source code (for manual editing)

## Customization

You can edit the generated `.mmd` file and re-render it, or modify the script
to:

- Adjust `max_depth` to control how deep the analysis goes
- Modify `max_items_per_group` to limit items per group
- Add custom relationship detection logic
- Change color schemes

## Requirements

- Python 3.6+
- Internet connection (for rendering SVG via mermaid.ink API)

## Troubleshooting

If SVG rendering fails, the script will:

1. Save the Mermaid source (`.mmd` file)
2. Provide a link to manually convert at https://mermaid.live/

You can also use the Mermaid source directly in:

- GitHub/GitLab markdown (renders automatically)
- Mermaid Live Editor: https://mermaid.live/
- VS Code with Mermaid extension
