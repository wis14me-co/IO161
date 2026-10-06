engineer-2
stages/stage-2/engineer_2_tasks.md

Stage 2 Tasks - Engineer 2 (Infrastructure/Frontend Serving) - Bulk Assignment
- Task 1: HTML Content Negotiation - Accept header routing: text/html -> serve UI, application/json -> API for all routes
- Task 2: Static Asset Pipeline - Embed all frontend assets in Docker image, no external CDN deps, include in multi-stage build
- Task 3: Dockerfile Updates for Frontend - Build final image < 2GB, start < 60s, all assets self-contained
- Task 4: Session/Cookie Auth for Browser - Cookie-based session support alongside bearer tokens, HttpOnly/Secure/SameSite=Lax
- Task 5: CSRF Protection - CSRF tokens for browser state-changing forms, double-submit cookie pattern
- Task 6: Frontend Build & Test Integration - CI pipeline integration, production build output to static dir, data-testid attributes
- Task 7: Stage 1 Import Compatibility Testing - Verify Stage 2 service imports Stage 1 exports correctly

Goals: resource efficient, fast, aesthetic/professional design, plug-and-play frontend serving.