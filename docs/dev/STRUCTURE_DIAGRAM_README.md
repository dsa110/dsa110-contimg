# Directory Structure Diagram Generator

A generalized script that automatically analyzes any directory structure and
generates a Mermaid flowchart diagram showing the organization and relationships
between modules.

## Location

The script is located at: `backend/scripts/dev/generate_structure_diagram.py`

## Usage

Run from the repository root or backend directory:

```bash
# From repository root
python backend/scripts/dev/generate_structure_diagram.py <directory_path> [output.svg]

# From backend directory
python scripts/dev/generate_structure_diagram.py <directory_path> [output.svg]
```

### Examples

**Generate diagram for backend:**

```bash
cd /data/dsa110-contimg
python backend/scripts/dev/generate_structure_diagram.py backend docs/architecture/diagrams/backend_structure.svg
```

**Generate diagram for frontend:**

```bash
python backend/scripts/dev/generate_structure_diagram.py frontend docs/architecture/diagrams/frontend_structure.svg
```

**Generate diagram for any directory:**

```bash
python backend/scripts/dev/generate_structure_diagram.py docs docs/architecture/diagrams/docs_structure.svg
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

  - `conversion → calibration → imaging → photometry → catalog`
  - `api → database`, `api → conversion`
  - `pipeline → conversion/calibration/imaging`
  - `utils → conversion/calibration/imaging`

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

## Related

- [Architecture Diagrams](../architecture/diagrams/) - Generated diagrams
- [Backend Structure](../architecture/BACKEND_STRUCTURE.md) - Backend documentation
