# Frozen-Flask GitHub Pages Deployment Guide

## 🎯 Why These Settings Are Critical

### **FREEZER_RELATIVE_URLS = True**

**Problem**: Without this, Frozen-Flask generates absolute paths like `/static/css/style.css`

**Issue on GitHub Pages**: When hosted at `username.github.io/repo-name/`, the browser looks for:
```
username.github.io/static/css/style.css  ❌ (404 error)
```

**Solution**: With `FREEZER_RELATIVE_URLS = True`, paths become:
```
./static/css/style.css  ✅ (works in any subfolder)
```

**Why This Matters**: GitHub Pages often hosts sites in subdirectories, breaking absolute paths.

---

### **FREEZER_BASE_URL Configuration**

**Problem**: Any absolute links or redirects need the correct base URL

**Issue**: Wrong base URL causes:
- Broken navigation
- Incorrect form actions
- Failed redirects
- Missing assets

**Solution**: Set to your exact GitHub Pages URL:
```python
# For username.github.io/repo-name/
FREEZER_BASE_URL = 'https://username.github.io/FinancialReportingSystem/'

# For username.github.io/ (custom domain)
FREEZER_BASE_URL = 'https://username.github.io/'
```

**Why This Matters**: Ensures all generated URLs point to the correct location.

---

### **Automatic Route Discovery**

**Problem**: Manual registration of every route is error-prone

**Solution**: Frozen-Flask automatically discovers all `@app.route()` decorators

**What Gets Discovered**:
- All static routes (`/`, `/about`, `/upload`)
- Template variables in those routes
- URL parameters and query strings

**Why This Matters**: Reduces maintenance and prevents missing pages.

---

### **@freezer.register_generator**

**Problem**: Dynamic routes with parameters aren't linked in navigation

**Example**: `/reports/123`, `/blog/post-title`, `/user/profile`

**Solution**: Register generators for dynamic content:
```python
@freezer.register_generator
def financial_statements():
    statements = ['statement-financial-position', 'statement-financial-performance']
    for statement in statements:
        yield f'/{statement}', {'statement_type': statement}
```

**Why This Matters**: Ensures all possible URL variations are generated.

---

### **MIME Types & Extensions**

**Problem**: GitHub Pages needs correct file extensions and MIME types

**Issues Without This**:
- `.html` files served as plain text
- CSS/JS files with wrong content types
- 404 errors for missing extensions

**Solution**: Frozen-Flask handles:
- Correct `.html` extensions
- Proper MIME type headers
- Static asset linking

**Why This Matters**: GitHub Pages serves files correctly without configuration.

---

## 🚀 Setup Instructions

### **1. Install Dependencies**

```bash
pip install -r requirements-frozen.txt
```

### **2. Configure Base URL**

Edit `freeze_app.py` and update:
```python
FREEZER_BASE_URL = 'https://[your-username].github.io/FinancialReportingSystem/'
```

Or use command line:
```bash
python freeze_app.py --username yourusername --repo FinancialReportingSystem
```

### **3. Generate Static Site**

```bash
# Basic generation
python freeze_app.py

# With custom username/repo
python freeze_app.py --username yourusername --repo FinancialReportingSystem

# Verify existing build
python freeze_app.py --verify-only
```

### **4. Test Locally**

```bash
cd build
python -m http.server 8000
```

Visit: http://localhost:8000

### **5. Deploy to GitHub Pages**

**Option A: Manual Deployment**
```bash
# Copy to docs folder
rm -rf docs/*
cp -r build/* docs/

# Commit and push
git add docs/
git commit -m "Update static site"
git push origin main
```

**Option B: GitHub Actions (Automatic)**
- Push to main branch
- GitHub Actions automatically builds and deploys
- Site available at: `https://[username].github.io/FinancialReportingSystem/`

---

## 📁 Generated Structure

```
build/
├── index.html                    # Home page
├── upload.html                   # Upload page
├── about.html                   # About page
├── reports.html                 # Reports listing
├── admin.html                   # Admin panel
├── export.html                  # Export page
├── login.html                   # Login page
├── results.html                 # Results page
├── statement-financial-position.html    # Financial position
├── statement-financial-performance.html  # Financial performance
├── statement-cash-flows.html           # Cash flows
├── reports/
│   ├── sample-2024-q1.html    # Dynamic report pages
│   ├── sample-2024-q2.html
│   └── sample-2024-q3.html
└── static/
    ├── css/
    │   ├── styles.css
    │   ├── variables.css
    │   └── ... (all CSS files)
    ├── js/
    │   ├── main.js
    │   ├── upload.js
    │   └── ... (all JS files)
    └── images/                  # If you have images
```

---

## 🔧 Advanced Configuration

### **Custom Route Generators**

For blog posts, user profiles, or dynamic content:

```python
@freezer.register_generator
def blog_posts():
    posts = [
        {'id': 'getting-started', 'title': 'Getting Started'},
        {'id': 'advanced-features', 'title': 'Advanced Features'}
    ]
    
    for post in posts:
        yield f'/blog/{post["id"]}', {'post': post}

@app.route('/blog/<post_id>')
def blog_post(post_id):
    # Generate blog post page
    pass
```

### **Custom MIME Types**

For special file types:

```python
FREEZER_MIMETYPES = {
    '.xml': 'application/xml',
    '.json': 'application/json',
    '.rss': 'application/rss+xml'
}
```

### **URL Removal Options**

```python
# Remove .html extensions (optional)
FREEZER_REMOVE_EXTRA_SLASH = True

# Generate clean URLs
# /about instead of /about.html
```

---

## 🐛 Troubleshooting

### **Issue: CSS Not Loading**

**Symptom**: Styles missing, page looks plain

**Cause**: Wrong base URL or absolute paths

**Solution**:
```python
FREEZER_RELATIVE_URLS = True  # Must be True
FREEZER_BASE_URL = 'https://username.github.io/repo-name/'  # Exact URL
```

### **Issue: 404 Errors on Assets**

**Symptom**: Console shows 404 for CSS/JS files

**Cause**: Static files not copied or wrong paths

**Solution**:
```bash
# Verify static files in build
ls -la build/static/

# Check paths in HTML
grep "href="static" build/*.html
```

### **Issue: Navigation Links Broken**

**Symptom**: Clicking navigation goes to wrong URLs

**Cause**: Base URL mismatch

**Solution**:
```bash
# Regenerate with correct URL
python freeze_app.py --username yourusername --repo YourRepoName
```

### **Issue: GitHub Pages Not Updating**

**Symptom**: Pushed changes but site unchanged

**Cause**: GitHub Pages build failure

**Solution**:
1. Check Actions tab for build errors
2. Verify GitHub Pages settings
3. Check for syntax errors in templates

---

## 🎯 Best Practices

### **1. Always Use Relative URLs**
```python
FREEZER_RELATIVE_URLS = True  # Never set to False for GitHub Pages
```

### **2. Test Locally First**
```bash
python freeze_app.py
cd build && python -m http.server 8000
# Test all pages before deploying
```

### **3. Use GitHub Actions**
- Automatic deployment on push
- Consistent builds
- Rollback capability

### **4. Monitor Build Logs**
- Check GitHub Actions for errors
- Verify all routes are generated
- Ensure assets are included

### **5. Keep Base URL Updated**
```python
# Update when changing repository name
FREEZER_BASE_URL = 'https://new-username.github.io/new-repo-name/'
```

---

## ✅ Success Criteria

Your static site is ready when:

1. **All pages generate without errors**
2. **CSS and JS load correctly** (check console)
3. **Navigation works between pages**
4. **Relative paths work** (no broken assets)
5. **Responsive design functions**
6. **GitHub Pages deployment succeeds**
7. **Site loads at correct URL**

---

**Status**: Configured for production GitHub Pages deployment! 🚀
