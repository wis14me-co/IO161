# Combined Stage 2 - Pocketful Payment System

## Stage 2 Directive
**STAGE 1, 2, 3 AND 4 COMBINED WILL BE STAGE 2**
- Stage 2 = Stage 1 with GUI + important parts of stages 2, 3 and 4
- All Stage 1 errors must be fixed before Stage 2 progression
- Engineer 3 is in charge of inference/GUI related tasks

## Task Overview
- **Task ID**: stage2-combined
- **Subject**: Combined Stage 2 implementation - Backend, Infrastructure, and Frontend
- **Status**: pending
- **Priority**: 1 (highest)

## Architecture Diagram
```arch
{
  "kind": "layered",
  "title": "Pocketful Payment System - Stage 2 Combined",
  "layers": [
    { "id": "ui", "title": "Browser", "items": [
      { "id": "api_client", "label": "API Client" }
    ] },
    { "id": "api", "title": "API", "items": [
      { "id": "fastapi", "label": "FastAPI App" }
    ] },
    { "id": "service", "title": "Service Layer", "items": [
      { "id": "auth", "label": "Auth Service" },
      { "id": "payment", "label": "Payment Service" },
      { "id": "split", "label": "Split Service" },
      { "id": "settlement", "label": "Settlement Service" },
      { "id": "authorization", "label": "Authorization Service" }
    ] },
    { "id": "data", "title": "Data Store", "items": [
      { "id": "users", "label": "Users Table" },
      { "id": "payments", "label": "Payments Table" },
      { "id": "requests", "label": "Requests Table" },
      { "id": "splits", "label": "Splits Table" },
      { "id": "authorizations", "label": "Authorizations Table" }
    ] }
  ],
  "flows": [
    { "from": "api_client", "to": "fastapi", "label": "HTTPS / JSON" },
    { "from": "fastapi", "to": "auth", "label": "Auth Endpoints" },
    { "from": "fastapi", "to": "payment", "label": "Payment Endpoints" },
    { "from": "fastapi", "to": "split", "label": "Split Endpoints" },
    { "from": "fastapi", "to": "settlement", "label": "Settlement Endpoints" },
    { "from": "fastapi", "to": "authorization", "label": "Auth Endpoints" },
    { "from": "auth", "to": "users", "label": "User Lookup" },
    { "from": "payment", "to": "users", "label": "User Balance Lookup" },
    { "from": "payment", "to": "payments", "label": "Create/Read Payments" },
    { "from": "split", "to": "users", "label": "User Handle Lookup" },
    { "from": "split", "to": "requests", "label": "Create Requests" },
    { "from": "settlement", "to": "users", "label": "Operator Check" },
    { "from": "settlement", "to": "payments", "label": "Create Settlement Payments" },
    { "from": "authorization", "to": "users", "label": "User Lookup" },
    { "from": "authorization", "to": "payments", "label": "Create Payments on Capture" },
    { "from": "authorization", "to": "split", "label": "Authorization Affects Split Calculation" },
    { "from": "payment", "to": "authorization", "label": "Payment Linked to Authorization Capture" }
  ]
}
```

## Component IDs for Linking
- `api`, `service`, `data` - Main system components
- `auth`, `payment`, `split`, `settlement`, `authorization` - Service sub-components

## Combined Stage 2 Tasks

### Engineer 1 (Backend/API) Tasks
1. Remove redundant validate_amount() calls - schemas already validate amount
2. Fix held calculation in me endpoint - include both outgoing and incoming authorizations
3. Add expires_at validation in create_authorization - RFC3339 format validation
4. Fix operator check efficiency in create_settlement - use set for O(1) lookup
5. Verify export/import compatibility for authorizations
6. Implement authorization API endpoints (POST /authorizations, GET /authorizations, POST /authorizations/{id}/capture, POST /authorizations/{id}/void)
7. Update balance model returning total/available/held with proper held calculation

### Engineer 2 (Infrastructure/Platform) Tasks
1. HTML Content Negotiation - Accept header routing: text/html -> UI, application/json -> API
2. Static Asset Pipeline - Embed all frontend assets in Docker image, no external CDN deps
3. Dockerfile Updates for Frontend - Build frontend, final image < 2GB, starts < 60s
4. Session/Cookie Auth for Browser - Cookie-based session support alongside bearer tokens
5. CSRF Protection - CSRF tokens for browser state-changing forms (pay, request, split, authorize, capture, void)
6. Frontend Build & Test Integration - Add frontend lint/test to CI pipeline

### Engineer 3 (Frontend/UI - Primary Owner) Tasks
1. Design System & Base Layout - Color palette, typography scale, spacing scale, component library, responsive
2. Auth Screens (/signup, /login) - Forms with data-testid attributes, accessible labels, focus states
3. Home Dashboard (/)- Balance & Pay/Request Forms - wallet-balance, wallet-available, wallet-held, pay form, request form
4. Activity Feed (/) - Activity list with visibility icons, empty state, newest first
5. Requests Screen (/requests) - Two columns: incoming-list and outgoing-list with status buttons
6. Split Screen (/split) - Live split-preview with computed shares per spec §9
7. Authorizations Screen (/authorizations) - authorization-list with capture/void buttons, RFC3339 expires
8. Wallet Refresh & Uncertainty Handling - wallet-refresh button, pay-uncertain on network loss, idempotency key retry
9. Responsive & Accessibility Audit - Verify all screens at 375px and desktop, keyboard navigation, focus visible, contrast ratios, ARIA labels

## Goals
- Resource efficient - optimized operator checks, efficient validation paths
- Fast to run - minimal overhead, efficient paths
- Aesthetic/professional design - cohesive visual system, trustworthy finance UI
- Plug-and-play - easy setup, can be set up very quickly

## Room Plan & Diagram
- Publishing architecture.json and plan.md to room with Stage 2 combined snapshot
- Engineer 3 assumes vision's role as planner while vision is inactive