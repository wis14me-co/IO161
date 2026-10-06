# Stage 2 Tasks - Engineer 3 (Frontend/UI - Primary Owner)

## Task 1: Design System & Base Layout
Create cohesive visual system: color palette (trustworthy finance blues/greens), typography scale, spacing scale, component library (buttons, inputs, selects, cards, tables). Responsive: 375px mobile to desktop. CSS custom properties. No external frameworks.

## Task 2: Auth Screens (/signup, /login)
Build signup/login forms with data-testid: signup-email/password/display-name/submit, login-email/password/submit, auth-error, current-user, current-handle, logout-button. Handle derivation preview. Accessible labels, focus states, error handling.

## Task 3: Home Dashboard (/) - Balance & Pay/Request Forms
Implement wallet balance display: wallet-balance (total), wallet-available (headline), wallet-held (when >0). Pay form: pay-handle, pay-amount (decimal input), pay-note, pay-visibility (public/private), pay-submit, pay-error, pay-uncertain. Request form: request-handle/amount/note/submit/error. Preserve form values on success. Decimal parsing per minor_units.

## Task 4: Activity Feed (/)
Build activity-list with activity-item-{payment_id}, data-visibility, activity-parties, activity-amount, activity-note. Empty state: empty-activity. Newest first. Visibility icons for public/private.

## Task 5: Requests Screen (/requests)
Two columns: incoming-list and outgoing-list. request-item-{id} with data-status. request-amount, request-pay/decline/cancel buttons per status rules. request-error for failed actions. empty-requests state.

## Task 6: Split Screen (/split)
split-amount (decimal), split-handles (comma-separated), split-note, split-submit, split-error. Live split-preview with split-share-{handle} showing computed shares per spec §9 before submit. Identical to server calculation.

## Task 7: Authorizations Screen (/authorizations)
authorization-list with authorization-item-{id}, data-status. authorization-amount, authorization-captured (when captured), authorization-expires (RFC3339). Incoming open: authorization-capture-amount (prefilled remainder), authorization-capture button. Outgoing open: authorization-void button. authorization-error, empty-authorizations.

## Task 8: Wallet Refresh & Uncertainty Handling
wallet-refresh button on /. Latest refresh wins (cancel previous in-flight). Pay/refund uncertainty: show pay-uncertain on network loss, retry with same idempotency key. Request stale pay button disappears on refresh.

## Task 9: Responsive & Accessibility Audit
Verify all screens at 375px and desktop. Keyboard navigation, focus visible, contrast ratios, ARIA labels, screen reader friendly. Empty/loading/error states for all data.