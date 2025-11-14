# GitHub Pages Troubleshooting Guide

**Date:** 2025-11-12

## Common Issues and Solutions

### Issue 1: 404 Error - "There isn't a GitHub Pages site here"

**Symptoms:**

- Visiting `dsa110-contimg.github.io/dsa110-contimg/` shows 404
- GitHub Pages error page appears

**Solutions:**

#### Step 1: Enable GitHub Pages in Repository Settings

1. Go to: `https://github.com/dsa110/dsa110-contimg/settings/pages`
2. Under **"Source"**:
   - Select: **"Deploy from a branch"**
   - Branch: **"gh-pages"** / **"/ (root)"**
   - Folder: **"/ (root)"**
   - Click **"Save"**

**Important:** The `gh-pages` branch will be created automatically by the
workflow on first deployment.

#### Step 2: Verify Workflow Ran Successfully

1. Go to: `https://github.com/dsa110/dsa110-contimg/actions`
2. Look for **"Docs Build and Deploy"** workflow
3. Check if it completed successfully (green checkmark)
4. If it failed, click on it to see error details

#### Step 3: Check if gh-pages Branch Exists

1. Go to: `https://github.com/dsa110/dsa110-contimg/branches`
2. Look for `gh-pages` branch
3. If it doesn't exist, the workflow hasn't run yet or failed

#### Step 4: Manually Trigger Workflow (if needed)

1. Go to: `https://github.com/dsa110/dsa110-contimg/actions`
2. Click **"Docs Build and Deploy"** workflow
3. Click **"Run workflow"** button (top right)
4. Select branch: **jakob-wdash** (or **main**)
5. Click **"Run workflow"**

### Issue 2: Workflow Runs But Site Still Shows 404

**Possible Causes:**

1. **GitHub Pages not enabled:**
   - Go to Settings → Pages
   - Ensure "Deploy from a branch" is selected
   - Branch should be `gh-pages` / `root`

2. **Wrong branch selected:**
   - GitHub Pages must be set to deploy from `gh-pages` branch
   - Not from `main` or `jakob-wdash`

3. **Deployment failed:**
   - Check Actions tab for errors
   - Look at "Deploy to GitHub Pages" step logs

4. **Wait time:**
   - First deployment can take 5-10 minutes
   - GitHub Pages updates can take 1-2 minutes after deployment

### Issue 3: Workflow Doesn't Trigger

**Check:**

1. **Branch name:**
   - Workflow triggers on: `main`, `master`, `jakob-wdash`
   - Ensure you're pushing to one of these branches

2. **File paths:**
   - Workflow only triggers on changes to:
     - `docs/**`
     - `mkdocs.yml`
     - `.github/workflows/docs.yml`
     - docs/javascripts/ (custom JavaScript)
   - If you changed other files, workflow won't trigger

3. **Workflow file:**
   - Verify `.github/workflows/docs.yml` exists
   - Check syntax is valid (YAML)

### Issue 4: Custom Domain (code.deepsynoptic.org)

If your site is actually hosted at
`http://code.deepsynoptic.org/dsa110-contimg/`:

1. **This is NOT GitHub Pages** - it's a custom server/reverse proxy
2. The GitHub Pages workflow still deploys to `gh-pages` branch
3. Your custom server likely pulls from `gh-pages` branch or has its own
   deployment
4. Check with your server administrator about the deployment process

## Verification Steps

### 1. Check Workflow Status

```bash
# View recent commits
git log --oneline -5

# Check if workflow file exists
cat .github/workflows/docs.yml | grep -A 5 "Deploy to GitHub Pages"
```

### 2. Verify GitHub Pages Settings

- URL: `https://github.com/dsa110/dsa110-contimg/settings/pages`
- Should show: "Your site is live at..." (if enabled)
- Source: `gh-pages` branch

### 3. Check gh-pages Branch

- URL: `https://github.com/dsa110/dsa110-contimg/tree/gh-pages`
- Should contain `index.html` and other site files
- If branch doesn't exist, workflow hasn't deployed yet

### 4. Test Local Build

```bash
# Build locally to verify MkDocs works
/opt/miniforge/envs/casa6/bin/python -m mkdocs build

# Check if site/ directory was created
ls -la site/
```

## Quick Fix Checklist

- [ ] GitHub Pages enabled in Settings → Pages
- [ ] Source set to `gh-pages` branch
- [ ] Workflow ran successfully (check Actions tab)
- [ ] `gh-pages` branch exists (check Branches tab)
- [ ] Waited 2-3 minutes after deployment
- [ ] Hard refresh browser (Ctrl+F5 / Cmd+Shift+R)

## Still Not Working?

1. **Check GitHub Actions logs:**
   - Go to Actions → Click failed workflow → Check error messages

2. **Verify repository permissions:**
   - Workflow needs write access to create `gh-pages` branch
   - `GITHUB_TOKEN` should have sufficient permissions

3. **Check for workflow errors:**
   - Look for red X marks in Actions tab
   - Read error messages in workflow logs

4. **Manual deployment test:**
   - Build locally: `mkdocs build`
   - Manually create `gh-pages` branch and push `site/` directory
   - See if GitHub Pages picks it up

## Contact Points

- **Repository:** `https://github.com/dsa110/dsa110-contimg`
- **Actions:** `https://github.com/dsa110/dsa110-contimg/actions`
- **Settings:** `https://github.com/dsa110/dsa110-contimg/settings/pages`
- **Branches:** `https://github.com/dsa110/dsa110-contimg/branches`
