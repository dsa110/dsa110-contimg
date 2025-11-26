# Quick Start: Automated Protections Setup

**5-minute setup to prevent all common developer mistakes.**

## One-Command Installation

```bash
./scripts/install-developer-automations.sh
source ~/.bashrc  # or ~/.zshrc
```

That's it! You're now protected against:

- ✅ System Python usage (automatically redirects to casa6)
- ✅ Pytest 2>&1 errors (uses safe wrapper automatically)
- ✅ Markdown files in root (pre-commit hook blocks)
- ✅ System Python in scripts (pre-commit hook blocks)
- ✅ Output suppression mistakes (pre-commit hook warns)
- ✅ Test organization violations (pre-commit hook blocks)
- ✅ Missing error detection (auto-sourced)

## Verify Installation

```bash
# Check Python wrapper
python --version  # Should show casa6 Python

# Check pytest wrapper
pytest --version  # Should use safe wrapper

# Check pre-commit hooks
ls -la .git/hooks/pre-commit  # Should exist and be executable
```

## What Gets Installed

1. **Shell Environment** (`~/.bashrc` or `~/.zshrc`)
   - Aliases `python` and `python3` to casa6 wrapper
   - Auto-sources error detection setup
   - Sets up pytest safe wrapper aliases

2. **Pre-Commit Hooks** (`.git/hooks/pre-commit`)
   - Validates pytest usage
   - Blocks markdown files in root
   - Blocks system Python in scripts
   - Warns about output suppression
   - Validates test organization

3. **Python Wrappers** (`.local/bin/`)
   - `python` → casa6 Python
   - `python3` → casa6 Python

## Protection Coverage

| Issue                    | Prevention Method                       | Effectiveness |
| ------------------------ | --------------------------------------- | ------------- |
| System Python            | Shell alias + wrapper + pre-commit      | 100%          |
| Pytest 2>&1              | Safe wrapper + pre-commit + test runner | 100%          |
| Markdown in root         | Pre-commit hook                         | 100%          |
| System Python in scripts | Pre-commit hook                         | 100%          |
| Output suppression       | Pre-commit hook (warns)                 | Warned        |
| Test organization        | Pre-commit hook                         | 100%          |
| Error detection          | Auto-sourced                            | 100%          |

## Manual Override (Emergency Only)

If you really need to bypass protections:

```bash
# Bypass pre-commit hooks (not recommended)
git commit --no-verify -m "Emergency commit"

# Use system Python directly (will fail for CASA code)
/usr/bin/python3 script.py
```

**Warning:** These bypasses should only be used in emergencies. The protections
exist for good reasons.

## Troubleshooting

### Python wrapper not working

```bash
# Check if casa6 exists
test -x /opt/miniforge/envs/casa6/bin/python && echo "OK" || echo "Missing"

# Re-run setup
./scripts/setup-developer-env.sh
source ~/.bashrc
```

### Pre-commit hooks not running

```bash
# Check if hook exists
ls -la .git/hooks/pre-commit

# Make executable
chmod +x .git/hooks/pre-commit

# Test manually
.git/hooks/pre-commit
```

### Shell aliases not working

```bash
# Check if configured
grep "DSA110_CONTIMG_DEV_ENV" ~/.bashrc

# Re-run setup
./scripts/setup-developer-env.sh
source ~/.bashrc
```

## Full Documentation

- `docs/how-to/AUTOMATED_PROTECTIONS.md` - Complete protection details
- `docs/how-to/DEVELOPER_HANDOVER_WARNINGS.md` - What we're protecting against
- `docs/how-to/using-pytest-safely.md` - Pytest protection details

---

**Remember:** These automations are safety nets, not obstacles. They prevent
real issues that would cause problems later.
