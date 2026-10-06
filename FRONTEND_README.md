# Frontend Implementation - Stage 2

## Overview
This document describes the frontend JavaScript implementation for Stage 2, including authorization list rendering, wallet-refresh with competing clients logic, and API client updates.

## Files Modified

### 1. `app/static/js/api.js`

#### Added Methods:
- **`listAuthorizations(direction, status, limit, offset)`**
  - GET request to `/authorizations` endpoint
  - Supports filtering by direction (incoming/outgoing) and status
  - Supports pagination with limit and offset

- **`captureAuthorization(authId, amount, final)`**
  - Updated to accept `amount` and `final` parameters
  - POST request to `/authorizations/{id}/capture`

## Files Modified

### 2. `app/static/js/app.js`

#### Pages.Authorizations Implementation:
- **`loadAuthorizations()`**
  - Calls `api.listAuthorizations()` to fetch authorizations
  - Renders authorization list with all data-testid attributes
  - Handles empty state with `.empty-authorizations` element
  - Binds capture/void button events

- **`handleAuthorizationAction(action, authId, button)`**
  - Handles capture and void actions
  - Shows error in `authorization-error` element
  - Handles network errors gracefully

- **`getStatusClass(status)`**
  - Returns CSS class based on authorization status
  - Supports: open, captured, voided, expired

#### Pages.Home Updates:
- **`refreshWallet()`**
  - Implements latest-refresh-wins logic
  - Tracks refresh ID to ignore stale responses
  - Properly handles concurrent refreshes

- **`loadWallet()`**
  - Added refresh ID tracking
  - Ignores stale responses
  - Updates all wallet elements

#### Helper Functions:
- All existing helper functions remain unchanged
- Error handling enhanced for network errors

## HTML Templates

### `app/templates/index.html`
- **Wallet Refresh Button** (line 94)
  - Already present in template
  - Calls `pages.home.refreshWallet()`
  - Has `data-originalText` for loading state

### `app/templates/authorizations.html`
- **Authorization List Container** (line 11)
  - `id="authorization-list"` for JavaScript rendering
- **Empty State** (line 14-16)
  - `.empty-authorizations` class for empty state display

## Key Features

### 1. Authorization List Rendering
- Displays all authorizations for the current user
- Shows incoming and outgoing authorizations
- Displays:
  - Party information (from/to handles)
  - Amount with sign (+/-)
  - Captured amount and remaining amount
  - Status with color coding
  - Note and expiry date (if available)
- Empty state handling

### 2. Authorization Actions
- **Capture**: For receivers to capture authorized funds
  - Shows remaining amount
  - Can capture partial or full amount
  - Final capture automatically when capturing all remaining
- **Void**: For payers to cancel authorizations
  - Only available for open authorizations
- Error handling in `authorization-error` element

### 3. Wallet Refresh with Latest-Refresh-Wins
- Tracks in-flight refreshes
- Uses refresh IDs to identify stale responses
- Automatically ignores old responses
- Prevents UI updates from stale data
- Handles network errors gracefully

### 4. Network Error Handling
- **Pay Uncertain**: Shows `pay-uncertain` element for network errors
- **Request Error**: Shows `request-error` element for payment refusals
- **Authorization Error**: Shows `authorization-error` element for action failures

## Testing

### Manual Testing Steps:

1. **Authorization List**
   - Navigate to `/authorizations`
   - Verify list loads correctly
   - Test capture action (as receiver)
   - Test void action (as payer)
   - Check error handling

2. **Wallet Refresh**
   - Navigate to `/`
   - Click "Refresh Balance"
   - Verify latest response is used
   - Test with slow network

3. **API Client**
   - Verify `listAuthorizations` method exists
   - Verify `captureAuthorization` accepts new parameters

### Browser Console Tests:
Run `testFrontend.js` in the browser console to verify all functionality.

## Styling

The authorization items use the following structure:
- `.authorization-item`: Main container
- `.authorization-header`: Party info and status
- `.authorization-party`: From → To handles
- `.authorization-status`: Status badge with color
- `.authorization-amount`: Amount with sign and color
- `.authorization-details`: Captured, remaining, note, expiry
- `.authorization-actions`: Button container
- `.authorization-error`: Error message display

## Status Colors
- **Positive**: Green (incoming payments/amounts)
- **Negative**: Red (outgoing payments/amounts)
- **Status badges**:
  - Open: Blue
  - Captured: Green
  - Voided: Gray
  - Expired: Orange

## Security Considerations

1. **Token Management**: All API calls use stored authentication token
2. **Idempotency**: API calls use idempotency keys for idempotent operations
3. **Error Handling**: All errors are caught and displayed to user
4. **Loading States**: All async operations show loading states

## Browser Compatibility

- Modern browsers with ES6+ support
- Fetch API support
- LocalStorage support
- Event delegation for dynamic elements

## Performance Optimizations

1. **Latest-Refresh-Wins**: Prevents stale data updates
2. **Event Delegation**: Binds events to parent containers
3. **Lazy Loading**: Only loads data when needed
4. **Pagination**: Supports limit and offset parameters

## Future Enhancements

1. **WebSocket Integration**: Real-time authorization updates
2. **Authorization Filtering**: Filter by status, direction, date range
3. **Authorization History**: View past captured/voided authorizations
4. **Bulk Actions**: Batch capture/void operations
5. **Search**: Search authorizations by handle or note
