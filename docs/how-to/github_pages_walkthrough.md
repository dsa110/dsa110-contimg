# GitHub Pages Setup Walkthrough

**Date:** 2025-11-12  
**Repository:** `dsa110/dsa110-contimg`

## Overview

This walkthrough explains how the GitHub Pages deployment is configured for this
project and how to use it.

## Current Configuration

### 1. MkDocs Configuration (`mkdocs.yml`)

```yaml
site_name: DSA-110 Continuum Imaging Pipeline
site_url: https://dsa110-contimg.github.io/dsa110-contimg/
repo_url: https://github.com/dsa110/dsa110-contimg
docs_dir: docs
```

**Key points:**

- `site_url`: Where your documentation will be hosted
  - Your actual domain: `http://code.deepsynoptic.org/dsa110-contimg/`
  - (Custom domain/reverse proxy setup, not standard GitHub Pages)
- `docs_dir`: Where your source documentation lives (`docs/` folder)

### 2. GitHub Actions Workflow (`.github/workflows/docs.yml`)

The workflow has three triggers:

**A. Push to main/master** (deploys to GitHub Pages)

```yaml
on:
  push:
    branches: [main, master]
    paths:
      - "docs/"
      - "mkdocs.yml"
      - ".github/workflows/docs.yml"
      - docs/javascripts/ (custom JavaScript)
```

**B. Pull Request** (builds and tests, but doesn't deploy)

```yaml
pull_request:
  paths: [...]
```

**C. Manual trigger** (workflow_dispatch - run from GitHub UI)

## Step-by-Step Setup

### Step 1: Enable GitHub Pages in Repository Settings

1. Go to your repository on GitHub: `https://github.com/dsa110/dsa110-contimg`
2. Click **Settings** (top menu)
3. Scroll down to **Pages** (left sidebar)
4. Under **Source**, select:
   - **Source:** Deploy from a branch
   - **Branch:** `gh-pages` / `root` (or `/ (root)`)
   - **Folder:** `/ (root)`
5. Click **Save**

**What happens:** GitHub creates a `gh-pages` branch (if it doesn't exist) and
serves files from it.

### Step 2: Verify Workflow is Ready

1. Go to **Actions** tab in your repository
2. You should see "Docs Build and Deploy" workflow
3. It will run automatically on the next push to `main`

### Step 3: Make a Test Change

Let's trigger the deployment:

```bash
# Make a small change to documentation
echo "<!-- Test update -->" >> docs/index.md

# Commit and push
git add docs/index.md
git commit -m "test: trigger GitHub Pages deployment"
git push origin main
```

### Step 4: Watch the Deployment

1. Go to **Actions** tab
2. Click on the running workflow "Docs Build and Deploy"
3. You'll see three jobs:
   - **Build MkDocs (strict)** - Builds the site
   - **Link check** - Validates links
   - **Mermaid visual checks** - Validates diagrams (if tests exist)

4. Watch the **Build** job:
   - It installs Python 3.11
   - Installs dependencies from `docs/requirements.txt`
   - Runs `mkdocs build --strict`
   - **Deploys to GitHub Pages** (only on push to main)

### Step 5: Verify Deployment

After the workflow completes (usually 2-3 minutes):

1. Go to **Actions** tab
2. Click the completed workflow run
3. Expand the **Deploy to GitHub Pages** step
4. You should see: "Deploying to GitHub Pages..."

5. Visit your site: `http://code.deepsynoptic.org/dsa110-contimg/`
   - It may take 1-2 minutes for GitHub to update the site
   - Hard refresh (Ctrl+F5) if you don't see changes

## How "Hot Reload" Works

### Automatic Rebuilds

Every time you push to `main` with changes to:

- `docs/` (any documentation file)
- `mkdocs.yml` (configuration)
- `.github/workflows/docs.yml` (workflow itself)
- docs/javascripts/ (custom JavaScript)

The workflow automatically:

1. ✅ Builds the documentation
2. ✅ Tests links and diagrams
3. ✅ Deploys to GitHub Pages
4. ✅ Updates the live site within 1-2 minutes

### Example Workflow

```
You edit docs/concepts/pipeline_overview.md
    ↓
git commit -m "Update pipeline docs"
    ↓
git push origin main
    ↓
GitHub Actions triggers automatically
    ↓
Workflow builds MkDocs (30-60 seconds)
    ↓
Workflow deploys to gh-pages branch (10-20 seconds)
    ↓
GitHub Pages updates live site (1-2 minutes)
    ↓
Your changes are live! 🎉
```

## Testing Before Deployment

### Local Testing

Before pushing, test locally:

```bash
# Build the site
/opt/miniforge/envs/casa6/bin/python -m mkdocs build

# Serve locally (with hot reload)
/opt/miniforge/envs/casa6/bin/python -m mkdocs serve
# Visit http://127.0.0.1:8001
```

### Pull Request Testing

When you open a PR:

- Workflow runs but **doesn't deploy**
- Validates that documentation builds successfully
- Checks links and diagrams
- You can see build errors before merging

## Troubleshooting

### Site Not Updating

1. **Check Actions tab:** Is the workflow running?
2. **Check workflow logs:** Look for errors in the "Build" job
3. **Wait 2-3 minutes:** GitHub Pages can take time to update
4. **Hard refresh:** Ctrl+F5 or Cmd+Shift+R

### Build Failures

Common issues:

**Missing dependencies:**

```bash
# Check docs/requirements.txt exists
cat docs/requirements.txt
```

**MkDocs errors:**

```bash
# Test build locally
/opt/miniforge/envs/casa6/bin/python -m mkdocs build --strict
```

**Link errors:**

- Check the "link-check" job in Actions
- Fix broken links in your markdown files

### Deployment Not Happening

Check:

1. ✅ Are you pushing to `main` or `master`?
2. ✅ Did you change files in `docs/` or `mkdocs.yml`?
3. ✅ Is GitHub Pages enabled in Settings → Pages?
4. ✅ Check workflow logs for errors

## Advanced Configuration

### Custom Domain

If you want a custom domain (e.g., `docs.yoursite.com`):

1. Add `CNAME` file to `docs/` directory:

   ```bash
   echo "docs.yoursite.com" > docs/CNAME
   ```

2. Update `mkdocs.yml`:

   ```yaml
   site_url: https://docs.yoursite.com/
   ```

3. Configure DNS with your domain provider

### Branch Protection

To prevent accidental deployments:

1. Go to Settings → Branches
2. Add rule for `main` branch
3. Require pull request reviews
4. Workflow will still deploy when PR is merged

### Manual Deployment

You can manually trigger deployment:

1. Go to **Actions** tab
2. Click **Docs Build and Deploy**
3. Click **Run workflow** button
4. Select branch (usually `main`)
5. Click **Run workflow**

## Summary

**Your setup:**

- ✅ Workflow configured (`.github/workflows/docs.yml`)
- ✅ MkDocs configured (`mkdocs.yml`)
- ✅ Automatic deployment on push to `main`
- ⏳ **Next step:** Enable GitHub Pages in repository settings

**After enabling GitHub Pages:**

- Push to `main` → Docs deploy automatically
- Changes go live in 1-2 minutes
- No manual steps needed!

## Quick Reference

**Repository:** `https://github.com/dsa110/dsa110-contimg`  
**Site URL:** `http://code.deepsynoptic.org/dsa110-contimg/`  
**Workflow:** `.github/workflows/docs.yml`  
**Build command:** `mkdocs build --strict`  
**Deploy branch:** `gh-pages` (auto-managed)
