// API Client for Pocketful Frontend
const API_BASE = '';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('pocketful_token') || null;
        this.csrfToken = this._getCsrfToken();
    }

    _getCsrfToken() {
        // Try to get CSRF token from meta tag
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta && meta.content) {
            return meta.content;
        }
        // Try from cookie
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
            const [name, value] = cookie.trim().split('=');
            acc[name.trim()] = value;
            return acc;
        }, {});
        if (cookies.csrftoken) {
            return cookies.csrftoken;
        }
        return null;
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('pocketful_token', token);
        } else {
            localStorage.removeItem('pocketful_token');
        }
    }

    getHeaders(includeIdempotency = false) {
        const headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        if (this.csrfToken) {
            headers['X-CSRF-Token'] = this.csrfToken;
        }
        if (includeIdempotency) {
            headers['Idempotency-Key'] = this.generateIdempotencyKey();
        }
        return headers;
    }

    generateIdempotencyKey() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }

    async request(method, path, body = null, includeIdempotency = false) {
        const options = {
            method,
            headers: this.getHeaders(includeIdempotency)
        };
        if (body) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${API_BASE}${path}`, options);
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new ApiError(response.status, data.code || 'error', data.message || 'Request failed', data);
        }
        return data;
    }

    get(path) { return this.request('GET', path); }
    post(path, body, includeIdempotency = true) { return this.request('POST', path, body, includeIdempotency); }

    // Auth
    async signup(email, password, displayName) {
        return this.post('/auth/signup', { email, password, display_name: displayName });
    }

    async login(email, password) {
        return this.post('/auth/login', { email, password });
    }

    async me() {
        return this.get('/me');
    }

    // Payments
    async pay(toHandle, amount, note, visibility) {
        return this.post('/payments', { to_handle: toHandle, amount, note, visibility });
    }

    // Requests
    async request(payerHandle, amount, note) {
        return this.post('/requests', { payer_handle: payerHandle, amount, note });
    }

    async listRequests(direction, status) {
        const params = new URLSearchParams();
        if (direction) params.append('direction', direction);
        if (status) params.append('status', status);
        return this.get(`/requests?${params.toString()}`);
    }

    async payRequest(requestId, visibility) {
        return this.post(`/requests/${requestId}/pay`, { visibility });
    }

    async declineRequest(requestId) {
        return this.post(`/requests/${requestId}/decline`);
    }

    async cancelRequest(requestId) {
        return this.post(`/requests/${requestId}/cancel`);
    }

    // Splits
    async createSplit(amount, handles, note) {
        return this.post('/splits', { amount, participant_handles: handles, note });
    }

    // Activity
    async getActivity(limit = 50, offset = 0) {
        return this.get(`/activity?limit=${limit}&offset=${offset}`);
    }

    // Authorizations
    async listAuthorizations(direction, status, limit, offset) {
        const params = new URLSearchParams();
        if (direction) params.append('direction', direction);
        if (status) params.append('status', status);
        if (limit) params.append('limit', limit);
        if (offset) params.append('offset', offset);
        return this.get(`/authorizations?${params.toString()}`);
    }

    async createAuthorization(toHandle, amount, note, visibility, expiresAt) {
        return this.post('/authorizations', { to_handle: toHandle, amount, note, visibility, expires_at: expiresAt });
    }

    async voidAuthorization(authId, idempotencyKey) {
        return this.post(`/authorizations/${authId}/void`, null, { idempotencyKey });
    }

    async captureAuthorization(authId, amount, final, idempotencyKey) {
        return this.post(`/authorizations/${authId}/capture`, { amount, final }, { idempotencyKey });
    }

    // Refunds
    async refundPayment(paymentId, amount) {
        return this.post(`/payments/${paymentId}/refunds`, { amount });
    }
}

class ApiError extends Error {
    constructor(status, code, message, data) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
        this.data = data;
    }
}

window.api = new ApiClient();