# Enhancement Tasks for Pocketful Payment System

## Goals
- Resource efficient - optimized operator checks, efficient validation paths
- Fast to run - minimal overhead, efficient paths
- Aesthetic/professional design - cohesive visual system, trustworthy finance UI
- Plug-in-play - easy setup, can be set up very quickly

## Task 1: Responsive Design Verification & Enhancement
**Priority:** High  
**Related to Plan.md Task 9: Responsive & Accessibility Audit**

### What needs doing:
- Verify all screens render correctly at 375px (mobile) and desktop widths
- Add responsive CSS media queries for key breakpoints
- Ensure touch-friendly hit targets (minimum 44px)
- Test navigation between all pages at mobile width

### Screens to verify:
- / (Home Dashboard) - wallet balance, forms, activity feed
- /login - login form
- /signup - signup form  
- /requests - incoming/outgoing requests list
- /split - split bill preview
- /authorizations - authorization list with capture/void

### Enhancements:
1. Add `meta viewport` tag to all templates
2. Add responsive CSS for `.btn` components at mobile widths
3. Ensure forms stack vertically on mobile
4. Add responsive layout for activity feed at narrow widths
5. Test split form at mobile width (handles input should stack)

## Task 2: Accessibility Audit & Enhancement
**Priority:** High  
**Related to Plan.md Task 9: Responsive & Accessibility Audit**

### What needs doing:
- Verify ARIA labels on all interactive elements
- Ensure focus-visible outlines are present and sufficient contrast
- Add missing ARIA labels for icons and buttons
- Verify color contrast ratios meet WCAG AA (minimum 4.5:1)

### Enhancements:
1. Add `aria-label` to all buttons that only have icons
2. Add `aria-describedby` for error messages
3. Ensure focus-visible state is keyboard-navigable
4. Verify contrast ratios in design-system.css
5. Add `role="status"` to error message elements
6. Add `aria-live="polite"` for dynamic content updates

## Task 3: Design System Polish
**Priority:** Medium  
**Related to goals: aesthetic/professional design**

### What needs doing:
- Enhance visual consistency across all pages
- Add subtle micro-interactions
- Improve loading states
- Enhance empty states

### Enhancements:
1. Add skeleton loading states to forms
2. Improve empty state illustrations/messages
3. Add hover states to form inputs
4. Enhance button animations
5. Add consistent spacing using the design system scale

## Task 4: Plug-and-Play Setup Enhancement
**Priority:** Medium  
**Related to goals: easy setup**

### What needs doing:
- Improve Dockerfile for faster builds
- Ensure all dependencies are available
- Add setup scripts

### Enhancements:
1. Optimize Docker build context
2. Add health check endpoint documentation
3. Ensure frontend assets build properly in Docker
4. Verify all Python dependencies are listed

## Task 5: Performance Optimizations
**Priority:** Medium  
**Related to goals: resource efficient, fast to run**

### What needs doing:
- Optimize API response paths
- Reduce unnecessary re-renders
- Efficient validation paths

### Enhancements:
1. Add caching for frequently accessed data
2. Optimize the wallet refresh logic
3. Reduce API call frequency where possible
4. Improve JavaScript event delegation

---

**Test Plan:** After all enhancements, test the program by:
1. Running `python -m pytest tests/unit/` to verify all tests pass
2. Starting the server and verifying all pages load
3. Checking responsive design at mobile/desktop widths
4. Verifying accessibility with browser dev tools
5. Testing Docker setup