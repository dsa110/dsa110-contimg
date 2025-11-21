# How to Trigger GitHub Pages Deployment

**Date:** 2025-11-12

## Current Situation

- GitHub Pages is **enabled** and configured correctly
- Source: `gh-pages` branch
- Site URL: `http://code.deepsynoptic.org/dsa110-contimg/`
- **Last deployment: 3 days ago** (needs update)

## Steps to Trigger Deployment

### Option 1: Manual Workflow Trigger (Recommended)

1. Go to: `https://github.com/dsa110/dsa110-contimg/actions`
2. Click **"Docs Build and Deploy"** in the left sidebar
3. Click **"Run workflow"** button (top right, dropdown)
4. Select branch: **jakob-wdash** (or **main**)
5. Click **"Run workflow"** button
6. Wait for workflow to complete (2-3 minutes)
7. Wait additional 1-2 minutes for GitHub Pages to update

### Option 2: Push a Change to Trigger Workflow

The workflow triggers automatically on pushes to `main`, `master`, or
`jakob-wdash` when you change:

- Files in `docs/` directory
- `mkdocs.yml`
- `.github/workflows/docs.yml`
- Files in `docs/javascripts/`

**To trigger:**

```bash
# Make a small change
echo "<!-- Updated $(date) -->" >> docs/index.md

# Commit and push
git add docs/index.md
git commit -m "docs: trigger GitHub Pages deployment"
git push origin jakob-wdash
```

### Option 3: Check Why Workflow Didn't Run

1. Go to: `https://github.com/dsa110/dsa110-contimg/actions`
2. Check if there are any workflow runs for your recent commits
3. If no runs exist, check:
   - Are you pushing to `main`, `master`, or `jakob-wdash`?
   - Did you change files in the trigger paths?
   - Is the workflow file syntax correct?

## Verify Deployment

After workflow completes:

1. **Check Actions tab:**
   - Go to: `https://github.com/dsa110/dsa110-contimg/actions`
   - Find the completed workflow run
   - Expand "Deploy to GitHub Pages" step
   - Should see: "Deploying to GitHub Pages..."

2. **Check gh-pages branch:**
   - Go to: `https://github.com/dsa110/dsa110-contimg/tree/gh-pages`
   - Should see `index.html` and other site files
   - Check commit timestamp matches recent deployment

3. **Check GitHub Pages settings:**
   - Go to: `https://github.com/dsa110/dsa110-contimg/settings/pages`
   - "Last deployed" should update to current time
   - Site should be accessible at `http://code.deepsynoptic.org/dsa110-contimg/`

## Troubleshooting

### Workflow Runs But Doesn't Deploy

- Check workflow logs for errors
- Verify `GITHUB_TOKEN` has write permissions
- Ensure branch condition matches your branch name

### Workflow Doesn't Trigger

- Verify you're pushing to `main`, `master`, or `jakob-wdash`
- Check that files changed match trigger paths
- Verify `.github/workflows/docs.yml` exists and is valid YAML

### Deployment Succeeds But Site Doesn't Update

- Wait 2-3 minutes (GitHub Pages can be slow)
- Hard refresh browser (Ctrl+F5 / Cmd+Shift+R)
- Check if custom domain (`code.deepsynoptic.org`) has its own deployment
  process

## Quick Command Reference

```bash
# Check recent commits
git log --oneline -5

# Check current branch
git branch

# Trigger deployment by making a small change
echo "<!-- $(date) -->" >> docs/index.md
git add docs/index.md
git commit -m "docs: trigger deployment"
git push origin jakob-wdash
```
