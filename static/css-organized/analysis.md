# CSS Analysis - Working Files Structure

## Current Working Files
- `style.css` - Main stylesheet (1778 lines)
- `mobile-compact.css` - Mobile responsive styles (1735 lines)

## Analysis of style.css

### Global Variables (Lines 5-61)
```css
:root {
    /* Colors */
    --primary-900: #0a1128;
    --primary-800: #1e3a5f;
    --primary-700: #2c5282;
    --primary-600: #2b6cb0;
    --primary-500: #3182ce;
    --primary-400: #4299e1;
    
    --accent-gold: #d4a574;
    --accent-gold-light: #e8c9a0;
    --accent-emerald: #10b981;
    
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-700: #374151;
    --gray-800: #1f2937;
    --gray-900: #111827;
    
    --success: #10b981;
    --warning: #f59e0b;
    --error: #ef4444;
    --white: #ffffff;
    
    /* Shadows */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
    --shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    
    /* Typography */
    --font-display: 'DM Serif Display', Georgia, serif;
    --font-body: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    
    /* Spacing */
    --space-xs: 0.5rem;
    --space-sm: 0.75rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --space-2xl: 3rem;
    --space-3xl: 4rem;
    
    /* Border Radius */
    --radius-sm: 0.375rem;
    --radius-md: 0.5rem;
    --radius-lg: 0.75rem;
    --radius-xl: 1rem;
    
    /* Transitions */
    --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
    --transition-slow: 350ms cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Global Base Styles (Lines 63-96)
```css
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: var(--font-body);
    line-height: 1.6;
    color: var(--gray-800);
    background: linear-gradient(135deg, var(--gray-50) 0%, var(--gray-100) 100%);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

@keyframes slideDown { /* ... */ }
.container { /* ... */ }
```

### Global Components (Lines 98-400+)
- Navigation (navbar, nav-brand, nav-menu, mobile-menu-toggle)
- Buttons (.btn, .btn-primary, .btn-secondary, .btn-large)
- Hero section
- Feature cards
- Upload box
- Results cards
- Footer
- Loading spinner
- Alert messages

### Page-Specific Sections (Lines 400+)
- Demo section
- About page layouts
- Problem/solution boxes
- Features lists
- CTA sections
- Upload page specific styles

## Analysis of mobile-compact.css

### Responsive Breakpoints
- Tablet Portrait: 769px - 1024px
- Mobile: ≤768px  
- Tablet Landscape: 1025px - 1366px
- Small Mobile: ≤480px

### Mobile-Specific Variables
```css
:root {
    --mobile-space-xs: 0.25rem;
    --mobile-space-sm: 0.5rem;
    --mobile-space-md: 0.75rem;
    --mobile-space-lg: 1rem;
    --mobile-space-xl: 1.5rem;
    --mobile-space-2xl: 2rem;
}
```

## Global vs Page-Specific

### GLOBAL (Used on ALL pages):
1. **CSS Variables** - All color, spacing, typography variables
2. **Base Styles** - Reset, body, container
3. **Navigation** - navbar, mobile menu
4. **Buttons** - .btn, .btn-primary, etc.
5. **Typography** - fonts, text sizing
6. **Animations** - keyframes, transitions
7. **Utility Classes** - text-center, hidden, etc.

### PAGE-SPECIFIC:
1. **Hero Section** - Only on index.html
2. **Demo Section** - Only on index.html  
3. **Upload Components** - Only on upload.html
4. **About Page Layouts** - Only on about.html
5. **CTA Sections** - Multiple pages but different content

## JavaScript Analysis

### Global JavaScript (Used on ALL pages):
1. **main.js** - Smooth scroll, animations, intersection observers
2. **mobile-menu.js** - Mobile navigation functionality

### Page-Specific JavaScript:
1. **upload.js** - Only on upload.html

## Refactoring Strategy

### Step 1: Extract Global Components
Create `base.css` with:
- CSS variables
- Base styles (reset, body, container)
- Global animations
- Utility classes

### Step 2: Extract Global Components  
Create `components.css` with:
- Navigation
- Buttons
- Loading states
- Alerts
- Footer

### Step 3: Extract Layout Components
Create `layout.css` with:
- Hero section
- Demo section
- About page layouts
- Upload page layouts
- CTA sections

### Step 4: Keep Responsive Separate
Keep `mobile-compact.css` as-is since it's already well-organized

### Step 5: Create Main Entry Point
Create new `style.css` that imports:
- base.css
- components.css  
- layout.css
- mobile-compact.css

This approach maintains the exact same UI while organizing the code properly.
