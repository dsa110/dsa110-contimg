# Documentation Testing

This directory contains tests for validating documentation quality and
correctness.

## Mermaid Diagram Testing

The `test_mermaid_diagrams.py` script validates that all Mermaid diagrams in the
MkDocs documentation render correctly without syntax errors.

### Purpose

Mermaid diagrams can fail to render due to:

- Syntax errors in diagram definitions
- Configuration issues with the Mermaid plugin
- JavaScript loading problems

When a diagram fails, MkDocs displays a visual error indicator:

- Bomb icon (dark brown sphere with lit fuse)
- Text: "Syntax error in text"
- Version: "mermaid version 10.9.5"

This test automatically checks every page in the documentation to ensure all
diagrams render successfully.

### Usage

#### Quick Start

```bash
# Run the test (automatically installs Playwright if needed)
make docs-test-mermaid
```

#### Manual Execution

```bash
# Install dependencies
pip install playwright pyyaml
playwright install chromium

# Run the test
python3 tests/docs/test_mermaid_diagrams.py
```

### How It Works

1. **Page Discovery**: Parses `mkdocs.yml` to extract all pages from the
   navigation structure
2. **Server Management**: Starts `mkdocs serve` on `127.0.0.1:8001`
3. **Browser Automation**: Uses Playwright to navigate to each page
4. **Error Detection**: Checks for visual error indicators:
   - Text content: "Syntax error in text"
   - Text content: "mermaid version"
   - Error container elements
5. **Reporting**: Generates a detailed report with:
   - List of all tested pages
   - Failed pages with error details
   - Pages containing Mermaid diagrams
   - Execution statistics

### Test Results

Results are saved to
`tests/docs/results/mermaid_test_report_YYYYMMDD_HHMMSS.json` with:

- Test timestamp
- Total pages tested
- Success/failure counts
- Detailed results for each page including:
  - Page URL
  - Success status
  - Error messages (if any)
  - Number of Mermaid diagrams found
  - Page load time

### Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed
- `130`: Test interrupted by user (Ctrl+C)

### Requirements

- Python 3.7+
- MkDocs installed (`pip install -r docs/requirements.txt`)
- Playwright (`pip install playwright && playwright install chromium`)
- PyYAML (`pip install pyyaml`)

### CI/CD Integration

This test can be integrated into CI/CD pipelines to ensure documentation
quality:

```yaml
- name: Test Mermaid Diagrams
  run: make docs-test-mermaid
```

### Troubleshooting

**Server fails to start:**

- Ensure MkDocs is installed: `pip install -r docs/requirements.txt`
- Check if port 8001 is already in use
- Verify `mkdocs.yml` is valid

**Playwright errors:**

- Install Playwright: `pip install playwright && playwright install chromium`
- Ensure Chromium browser is installed

**Page load timeouts:**

- Some pages may take longer to load
- Increase timeout in script if needed (default: 30 seconds)

**False positives:**

- Verify the error detection logic matches current Mermaid error format
- Check browser console for additional error details
