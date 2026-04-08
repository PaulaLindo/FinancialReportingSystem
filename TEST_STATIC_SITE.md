# Static Site Testing Guide

## 🚀 Quick Start

### **Option 1: Use the Built-in Static Server (Recommended)**

```bash
# Start static server on port 8080
python serve_static.py --port 8080

# Or default port 8000
python serve_static.py
```

Then visit: http://localhost:8080

### **Option 2: Use Python's Simple Server**

```bash
cd docs
python -m http.server 8080
```

### **Option 3: Use VS Code Live Server**

1. Open `/docs/index.html` in VS Code
2. Install "Live Server" extension
3. Right-click → "Open with Live Server"

## 🔧 What Was Fixed

### **Login Form Issues**
- ❌ **Before**: `POST /login.html` → 501 Not Implemented
- ✅ **After**: JavaScript form handling + redirect to dashboard

### **Demo Credentials**
The static login now accepts any credentials but shows demo hints:
- Email: `cfo@sadpmr.gov.za`
- Password: `demo123`

### **Form Behavior**
- Form validation with JavaScript
- Success message and auto-redirect
- Error handling for empty fields

## 🌐 Testing Checklist

### **Basic Navigation**
- [ ] Dashboard loads at `index.html`
- [ ] Login page loads at `login.html`
- [ ] Navigation menu works between pages
- [ ] Mobile menu toggle works

### **Login Functionality**
- [ ] Login form accepts input
- [ ] Success message appears
- [ ] Redirects to dashboard after login
- [ ] Demo credentials hint displays

### **Responsive Design**
- [ ] Mobile layout works (resize browser)
- [ ] Tablet layout works
- [ ] Desktop layout works
- [ ] Touch-friendly on mobile

### **Styling and Assets**
- [ ] CSS loads properly (no broken styles)
- [ ] JavaScript functions work
- [ ] Images and icons load
- [ ] Animations play correctly

### **Financial Pages**
- [ ] Upload page displays correctly
- [ ] Reports page shows sample data
- [ ] Admin page accessible
- [ ] About page loads

## 🐛 Common Issues & Solutions

### **Issue: 404 Errors**
```
GET /.well-known/appspecific/com.chrome.devtools.json HTTP/1.1" 404
```
**Solution**: This is normal Chrome DevTools behavior, ignore it.

### **Issue: CORS Errors**
**Solution**: Use the provided static server which includes CORS headers.

### **Issue: Forms Don't Work**
**Solution**: Run `python fix_static_login.py` to add JavaScript handling.

### **Issue: Styles Not Loading**
**Solution**: Ensure you're accessing via `http://localhost:PORT` not `file://`

### **Issue: Port Already in Use**
```bash
python serve_static.py --port 8081
```

## 📱 Mobile Testing

### **Chrome DevTools**
1. Open Developer Tools (F12)
2. Click device toggle
3. Test different screen sizes:
   - iPhone SE (375x667)
   - iPad (768x1024)
   - Desktop (1920x1080)

### **Real Device Testing**
1. Connect phone to same WiFi
2. Find your IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
3. Visit: `http://YOUR_IP:8080`

## 🚀 Deployment Testing

### **Before GitHub Pages**
1. Test locally with static server
2. Verify all pages load
3. Check responsive design
4. Test login functionality

### **After GitHub Pages**
1. Deploy: `python deploy_to_github_pages.py`
2. Wait 2-5 minutes for GitHub to process
3. Visit your GitHub Pages URL
4. Test all functionality

## 📊 Performance Testing

### **Page Load Speed**
- Open Developer Tools → Network tab
- Refresh page
- Check load times:
  - HTML: < 100ms
  - CSS: < 200ms
  - JS: < 300ms

### **Mobile Performance**
- Use Chrome Lighthouse
- Target scores:
  - Performance: > 90
  - Accessibility: > 95
  - Best Practices: > 90
  - SEO: > 90

## 🔍 Debugging

### **Console Errors**
Open Developer Tools → Console tab and check for:
- JavaScript errors
- Failed resource loads
- CORS issues

### **Network Issues**
Open Developer Tools → Network tab and check:
- 404 errors (missing files)
- Failed requests
- Slow loading resources

### **Styling Issues**
Open Developer Tools → Elements tab and check:
- CSS not applying
- Missing stylesheets
- Override conflicts

## ✅ Success Criteria

Your static site is ready when:

1. **All pages load without errors**
2. **Navigation works between all pages**
3. **Login form redirects to dashboard**
4. **Responsive design works on mobile**
5. **All CSS and JS assets load properly**
6. **No 404 errors for assets**
7. **Performance is acceptable (< 3 seconds load time)**

---

**Status**: Ready for local testing and GitHub Pages deployment! 🎉
