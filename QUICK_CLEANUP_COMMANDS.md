# Quick GitHub Pages Cleanup Commands

## Emergency Manual Cleanup (When Scripts Fail)

### Step 1: Force Close Locked Files

```bash
# Windows Command Prompt (Run as Administrator)
taskkill /F /IM python.exe
taskkill /F /IM code.exe  # If VS Code is locking files
```

### Step 2: Manual Repository Purge

```bash
# Delete docs folder contents manually
del /Q /S /F docs\*
rmdir /S /Q docs\*
mkdir docs
echo. > docs\.gitkeep
```

### Step 3: Manual Local Cleanup

```bash
# Delete build directories
rmdir /S /Q build
rmdir /S /Q dist
rmdir /S /Q output
rmdir /S /Q static_build
```

### Step 4: Fresh Generation with Cache Busting

```bash
# Generate with timestamp cache busting
python freeze_with_cache_busting.py --method timestamp
```

### Step 5: Manual Copy to docs

```bash
# Copy fresh build to docs
xcopy /E /I /Y build\* docs\
```

### Step 6: Empty Commit Trick

```bash
# Force GitHub Pages rebuild
git commit --allow-empty -m "trigger-rebuild-%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
git push origin main
```

### Step 7: Final Deployment

```bash
# Add and commit fresh deployment
git add docs/
git commit -m "Fresh deployment with cache busting - %date% %time%"
git push origin main
```

---

## PowerShell Alternative

```powershell
# Step 1: Force close processes
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name Code -Force -ErrorAction SilentlyContinue

# Step 2: Repository purge
Remove-Item -Recurse -Force docs\* -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force docs
Set-Content -Path docs\.gitkeep -Value ""

# Step 3: Local cleanup
Remove-Item -Recurse -Force build, dist, output, static_build -ErrorAction SilentlyContinue

# Step 4: Fresh generation
python freeze_with_cache_busting.py --method timestamp

# Step 5: Copy to docs
Copy-Item -Recurse -Force build\* docs\

# Step 6: Empty commit
git commit --allow-empty -m "trigger-rebuild-$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Step 7: Final deployment
git add docs/
git commit -m "Fresh deployment with cache busting - $(Get-Date -Format 'yyyyMMdd_HHmmss')"
git push origin main
```

---

## One-Line Emergency Command

```bash
# Complete cleanup in one command (run in admin terminal)
taskkill /F /IM python.exe && rmdir /S /Q docs build dist output static_build && mkdir docs && echo. > docs\.gitkeep && python freeze_with_cache_busting.py --method timestamp && xcopy /E /I /Y build\* docs\ && git add docs/ && git commit -m "Emergency fresh deployment" && git push origin main
```

---

## Verification Commands

```bash
# Check cache busting worked
find docs/ -name "*.v*.css" -o -name "*.v*.js"

# Check new version in HTML
grep "v[0-9]" docs/index.html

# Verify deployment
curl -I https://[username].github.io/[repo]/
```

---

## If All Else Fails: GitHub UI Method

1. **Go to GitHub Repository**
2. **Settings > Pages**
3. **Unpublish GitHub Pages** (temporarily)
4. **Wait 5 minutes**
5. **Re-publish GitHub Pages**
6. **Push fresh deployment**

This forces complete cache invalidation on GitHub's side.
