# GitHub Pages Setup Guide for Financial Reporting System

## Overview
Since your Flask application uses a `static/` folder that GitHub Pages cannot serve from directly, you need to maintain a `docs/` folder containing:
- **HTML files** (for your GitHub Pages site)
- **CSS files** (copied from `static/css/`)
- **JavaScript files** (copied from `static/js/`)

GitHub Pages is configured to serve from the `docs/` folder when enabled in repository settings.

## Folder Structure

```
FinancialReportingSystem/
├── static/                 ← Flask serves from here
│   ├── css/               ← Your development CSS
│   └── js/                ← Your development JS
├── docs/                  ← GitHub Pages serves from here
│   ├── css/               ← Synced from static/css/
│   ├── js/                ← Synced from static/js/
│   └── *.html             ← Static HTML pages
└── sync_static_to_docs.py ← Synchronization script
```

## Workflow

### 1. Make Changes to Static Assets
Always edit files in the `static/` folder (CSS/JS):
```
static/css/styles.css
static/js/main.js
etc.
```

### 2. Sync to Docs Folder
Run the sync script to copy changes to `docs/`:
```bash
python sync_static_to_docs.py
```

This will:
- Copy all CSS files from `static/css/` → `docs/css/`
- Copy all JS files from `static/js/` → `docs/js/`
- Report on what was synced

### 3. Commit and Push
```bash
# View changes
git status

# Stage static assets
git add docs/css/*
git add docs/js/*

# Stage sync script if first time
git add sync_static_to_docs.py

# Commit
git commit -m "Sync static assets to docs for GitHub Pages"

# Push
git push origin main
```

## File Reference

### Your Synced Static Assets
**CSS Files in `docs/css/`:**
- `styles.css` - Main stylesheet (imports others)
- `components.css` - UI components
- `layouts.css` - Page layouts
- `mobile.css` - Mobile responsive styles
- `desktop.css` - Desktop responsive styles
- `login.css` - Login page specific styles
- `variables.css` - CSS variables/custom properties

**JavaScript Files in `docs/js/`:**
- `main.js` - Main application logic
- `mobile-menu.js` - Mobile menu functionality
- `upload.js` - File upload handling
- `utils.js` - Utility functions

### HTML Files in `docs/`
Your static HTML pages should reference these as:
```html
<link rel="stylesheet" href="css/styles.css">
<script src="js/main.js"></script>
```

## GitHub Pages Configuration

### Enable GitHub Pages
1. Go to Repository Settings
2. Navigate to "Pages" section
3. Select:
   - **Source:** Deploy from a branch
   - **Branch:** main
   - **Folder:** /docs
4. Click Save

Your site will be available at: `https://PaulaLindo.github.io/FinancialReportingSystem/`

## Important Notes

### ✓ Do's
- Edit CSS/JS in `static/` folder
- Run sync script after making changes
- Commit synced files to docs/ folder
- Use relative paths in HTML: `href="css/styles.css"` (not `/static/css/styles.css`)

### ✗ Don'ts
- Directly edit files in `docs/css/` or `docs/js/`
- Commit changes to `static/` without syncing to `docs/`
- Forget to run the sync script before committing

## Troubleshooting

### Issue: GitHub Pages still shows old styling
**Solution:** 
1. Ensure files are synced: `python sync_static_to_docs.py`
2. Commit and push changes
3. Hard refresh in browser (Ctrl+Shift+R or Cmd+Shift+R)
4. Wait 1-2 minutes for GitHub Pages to rebuild

### Issue: Broken links on GitHub Pages
**Solution:**
- Ensure HTML files use relative paths: `href="css/styles.css"`
- NOT absolute paths like: `href="/static/css/styles.css"` or `href="{{ url_for(...) }}"`
- Check that files exist in `docs/css/` and `docs/js/`

### Issue: JavaScript errors in console
**Solution:**
- Verify JS files are in `docs/js/`
- Check script tags use correct paths: `src="js/main.js"`
- Ensure files were properly synced (no truncation)

## Automation Tips

### Add to Pre-commit Hook (Optional)
To automatically sync before commits, create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python sync_static_to_docs.py
if [ $? -ne 0 ]; then
    echo "Static sync failed. Commit aborted."
    exit 1
fi
```

### Add NPM Script (Optional)
In `package.json` (if you use npm):
```json
{
  "scripts": {
    "sync:static": "python sync_static_to_docs.py"
  }
}
```

## Current Status

✓ Sync script created: `sync_static_to_docs.py`
✓ Static assets synced to `docs/` folder
✓ All 7 CSS files copied to `docs/css/`
✓ All 4 JS files copied to `docs/js/`

Ready for GitHub Pages deployment!

