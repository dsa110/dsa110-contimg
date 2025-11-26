# How-To Guides

This directory contains step-by-step guides for common tasks.

## Quick Start

**New to the project?** Start here:

1. **Quick Setup** (Automated)

   ```bash
   ./scripts/quick-start.sh
   ```

   This automates everything! See `AUTOMATION_GUIDE.md` for details.

2. **Manual Setup**
   ```bash
   source scripts/developer-setup.sh
   ./scripts/auto-fix-common-issues.sh
   ```

## Essential Reading

- **[CRITICAL_HANDOVER_WARNINGS.md](../development/CRITICAL_HANDOVER_WARNINGS.md)** - ⚠️ READ
  FIRST
  - Common pitfalls and how to avoid them
  - Critical warnings for new developers

- **[AUTOMATION_GUIDE.md](../automation/AUTOMATION_GUIDE.md)** - 🚀 Automation Overview
  - What's automated and how it works
  - Setup workflows and troubleshooting

- **[QUICK_REFERENCE_CARD.md](QUICK_REFERENCE_CARD.md)** - 📋 Quick Reference
  - One-page cheat sheet
  - Most common commands

## Other Guides

- `agentic-session-setup.md` - Setting up error detection
- `adding-new-tests.md` - How to add new tests
- `PRETTIER_ENVIRONMENT_SPECIFIC.md` - Prettier configuration
- `PRETTIER_WARNINGS.md` - Prettier troubleshooting

## Getting Help

If you encounter issues:

1. Run `./scripts/validate-environment.sh`
2. Run `./scripts/auto-fix-common-issues.sh`
3. Check the relevant guide above
4. See `docs/concepts/` for conceptual documentation
