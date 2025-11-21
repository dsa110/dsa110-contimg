# GitHub Copilot Setup Guide

**Purpose**: Supplement Cursor's AI capabilities with GitHub Copilot  
**Date**: 2025-01-28  
**Status**: Setup Guide

---

## Overview

This guide covers two approaches to using GitHub Copilot with Cursor:

1. **Extension Installation** (Recommended) - Install GitHub Copilot extension
   directly in Cursor
2. **CLI via Docker** - Use GitHub Copilot CLI in a Docker container (for
   automation/scripts)

---

## Option 1: GitHub Copilot Extension in Cursor (Recommended)

Since Cursor is based on VS Code, you can install the GitHub Copilot extension
directly.

### Prerequisites

- Cursor installed and running
- GitHub account with Copilot subscription
- Active internet connection

### Installation Steps

1. **Open Cursor Extensions Panel**
   - Press `Ctrl+Shift+X` (or `Cmd+Shift+X` on Mac)
   - Or click the Extensions icon in the sidebar

2. **Search for GitHub Copilot**
   - Type "GitHub Copilot" in the search box
   - Look for the official extension by GitHub

3. **Install Extension**
   - Click "Install" on the GitHub Copilot extension
   - Wait for installation to complete

4. **Sign In**
   - After installation, Cursor will prompt you to sign in to GitHub
   - Follow the authentication flow
   - Grant necessary permissions

5. **Verify Installation**
   - Open any code file
   - Start typing - you should see Copilot suggestions appear
   - Look for the Copilot icon in the status bar

### Usage

- **Inline Suggestions**: Copilot will suggest code as you type
- **Accept Suggestions**: Press `Tab` to accept, or `Ctrl+→` to accept
  word-by-word
- **Dismiss**: Press `Esc` to dismiss suggestions
- **Trigger Manually**: Use `Ctrl+Enter` to open Copilot chat panel

### Configuration

You can configure Copilot behavior in Cursor settings:

```json
{
  "github.copilot.enable": {
    "*": true,
    "yaml": true,
    "plaintext": false
  },
  "github.copilot.editor.enableAutoCompletions": true
}
```

---

## Option 2: GitHub Copilot CLI via Docker

If you need the CLI tool for automation, scripts, or command-line usage, use
Docker to avoid GLIBC compatibility issues.

### Prerequisites

- Docker installed and running
- GitHub account with Copilot subscription

### Docker Setup

#### Step 1: Create Dockerfile

Create a Dockerfile for Copilot CLI:

```dockerfile
FROM node:20-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install GitHub Copilot CLI
RUN npm install -g @github/copilot

# Set working directory
WORKDIR /workspace

# Default command
CMD ["copilot", "--help"]
```

#### Step 2: Build Docker Image

```bash
docker build -t copilot-cli:latest -f Dockerfile.copilot .
```

#### Step 3: Create Wrapper Script

Create a wrapper script to run Copilot CLI easily:

```bash
#!/bin/bash
# scripts/copilot.sh - Wrapper for GitHub Copilot CLI in Docker

docker run --rm -it \
  -v "$(pwd):/workspace" \
  -v "$HOME/.config/github-copilot:/root/.config/github-copilot" \
  -w /workspace \
  copilot-cli:latest \
  copilot "$@"
```

Make it executable:

```bash
chmod +x scripts/copilot.sh
```

#### Step 4: Authenticate

First run will require authentication:

```bash
./scripts/copilot.sh auth login
```

Follow the authentication flow in your browser.

#### Step 5: Use Copilot CLI

```bash
# Get help
./scripts/copilot.sh --help

# Generate code
./scripts/copilot.sh generate "function to calculate fibonacci"

# Explain code
./scripts/copilot.sh explain path/to/file.py
```

### Alternative: Use Pre-built Image

You can also use a pre-built Node.js image with newer GLIBC:

```bash
docker run --rm -it \
  -v "$(pwd):/workspace" \
  -v "$HOME/.config/github-copilot:/root/.config/github-copilot" \
  -w /workspace \
  node:20-slim \
  sh -c "npm install -g @github/copilot && copilot $@"
```

---

## Troubleshooting

### Extension Issues

**Copilot not showing suggestions:**

- Check that you're signed in (look for Copilot icon in status bar)
- Verify your GitHub account has an active Copilot subscription
- Try reloading Cursor window (`Ctrl+Shift+P` → "Reload Window")

**Authentication issues:**

- Sign out and sign back in
- Check GitHub account permissions
- Verify internet connection

### CLI Issues

**GLIBC version error:**

- Use Docker approach (Option 2)
- Or upgrade system GLIBC (not recommended - can break other software)

**Docker permission errors:**

- Add user to docker group: `sudo usermod -aG docker $USER`
- Log out and back in for changes to take effect

**Authentication in Docker:**

- Ensure `~/.config/github-copilot` is mounted in container
- Run `copilot auth login` inside container

---

## Comparison: Extension vs CLI

| Feature                   | Extension | CLI               |
| ------------------------- | --------- | ----------------- |
| **Ease of Setup**         | ✓ Easy    | ✗ Requires Docker |
| **Real-time Suggestions** | ✓ Yes     | ✗ No              |
| **Editor Integration**    | ✓ Full    | ✗ None            |
| **Automation/Scripts**    | ✗ No      | ✓ Yes             |
| **Command-line Usage**    | ✗ No      | ✓ Yes             |
| **GLIBC Requirements**    | ✓ None    | ✗ Requires 2.28+  |

---

## Recommendation

**For most users**: Use the **Extension** (Option 1). It provides:

- Seamless integration with Cursor
- Real-time code suggestions
- No GLIBC compatibility issues
- No Docker setup required

**Use CLI only if**:

- You need to automate Copilot usage in scripts
- You want to use Copilot from command line
- You're building tools that integrate with Copilot API

---

## Related Documentation

- [GitHub Copilot Documentation](https://docs.github.com/en/copilot)
- [Cursor Documentation](https://cursor.sh/docs)
- [Docker Documentation](https://docs.docker.com/)

---

## Notes

- Both Cursor's AI and GitHub Copilot can run simultaneously
- Copilot suggestions may differ from Cursor's suggestions
- You can disable either tool if they conflict
- Copilot requires an active GitHub subscription ($10/month or free for
  students/teachers)
