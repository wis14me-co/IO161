engineer-2
stages

Stage 2 Tasks - Engineer 2 (Infrastructure/Frontend Serving):
- Task 1: HTML Content Negotiation - Accept header routing: text/html -> serve UI, application/json -> API. Apply to /, /requests, /split, /authorizations, /signup, /login. Reuse existing API logic.
- Task 2: Static Asset Pipeline - Embed all frontend assets (HTML, CSS, JS, fonts) in Docker image. No external CDN/runtime deps. Serve via static file handler with cache headers. Include in multi-stage build.
- Task 3: Dockerfile Updates for Frontend - Update Dockerfile to build frontend or copy pre-built assets. Ensure final image < 2GB, starts < 60s. All assets self-contained.
- Task 4: Session/Cookie Auth for Browser - Add cookie-based session support alongside bearer tokens for browser flows. HttpOnly, Secure, SameSite=Lax cookies. Login/signup sets cookie; logout clears it. API still uses Authorization header.
- Task 5: CSRF Protection - Implement CSRF tokens for browser state-changing forms (pay, request, split, authorize, capture, void). Double-submit cookie pattern. Validate on all mutating HTML form POSTs.
- Task 6: Frontend Build & Test Integration - Add frontend lint/test to CI pipeline. Ensure production build outputs to static dir. Test HTML routes return 200 with correct data-testid attributes.