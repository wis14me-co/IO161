// Main Application Logic for Pocketful Frontend

const formatMinorUnits = (minorUnits, currency = 'EUR') => {
    const abs = Math.abs(minorUnits);
    const whole = Math.floor(abs / 100);
    const cents = (abs % 100).toString().padStart(2, '0');
    const sign = minorUnits < 0 ? '-' : '';
    return `${sign}${whole}.${cents} ${currency}`;
};

const parseAmount = (str, currency = 'EUR') => {
    // Parse "15.00 EUR" or "15.00" to minor units
    const match = str.trim().match(/^([\d.]+)\s*(?:EUR)?$/i);
    if (!match) throw new Error('Invalid amount format');
    const parts = match[1].split('.');
    const whole = parseInt(parts[0] || '0', 10);
    const cents = (parts[1] || '0').padEnd(2, '0').slice(0, 2);
    return whole * 100 + parseInt(cents, 10);
};

// Announce message to screen readers
const announce = (message, polite = true) => {
    const liveRegion = document.getElementById('app-announcement');
    if (!liveRegion) {
        const el = document.createElement('div');
        el.id = 'app-announcement';
        el.setAttribute('role', 'status');
        el.setAttribute('aria-live', polite ? 'polite' : 'assertive');
        el.style.position = 'absolute';
        el.style.width = '1px';
        el.style.height = '1px';
        el.style.padding = '0';
        el.style.overflow = 'hidden';
        el.className = 'sr-only';
        document.body.appendChild(el);
    }
    const el = document.getElementById('app-announcement');
    if (el) {
        el.textContent = message;
    }
};

const showError = (elementId, message) => {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.style.display = 'block';
        // Also announce to screen readers
        announce(message, false);
    }
};

const hideError = (elementId) => {
    const el = document.getElementById(elementId);
    if (el) {
        el.style.display = 'none';
        el.textContent = '';
    }
};

const showUncertain = (elementId, message) => {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.style.display = 'block';
    }
};

const hideUncertain = (elementId) => {
    const el = document.getElementById(elementId);
    if (el) {
        el.style.display = 'none';
        el.textContent = '';
    }
};

const setLoading = (buttonId, loading) => {
    const btn = document.getElementById(buttonId);
    if (btn) {
        btn.disabled = loading;
        btn.textContent = loading ? 'Loading...' : btn.dataset.originalText || btn.textContent;
        if (loading) {
            btn.setAttribute('aria-busy', 'true');
        } else {
            btn.removeAttribute('aria-busy');
        }
    }
};

// Auth state management
const authState = {
    user: null,
    token: null,
    
    init() {
        this.token = localStorage.getItem('pocketful_token');
        if (this.token) {
            api.setToken(this.token);
            this.fetchMe();
        }
        this.updateAuthUI();
    },
    
    async fetchMe() {
        try {
            const data = await api.me();
            this.user = data;
            this.updateAuthUI();
            if (window.onAuthReady) window.onAuthReady(data);
        } catch (e) {
            this.logout();
        }
    },
    
    updateAuthUI() {
        const currentUser = document.getElementById('current-user');
        const currentHandle = document.getElementById('current-handle');
        const logoutButton = document.getElementById('logout-button');
        
        if (this.user) {
            if (currentUser) {
                currentUser.textContent = `${this.user.display_name} (${this.user.handle})`;
                currentUser.style.display = 'block';
            }
            if (currentHandle) {
                currentHandle.textContent = `@${this.user.handle}`;
            }
            if (logoutButton) {
                logoutButton.style.display = 'inline-flex';
            }
        } else {
            if (currentUser) currentUser.style.display = 'none';
            if (currentHandle) currentHandle.textContent = 'Not signed in';
            if (logoutButton) logoutButton.style.display = 'none';
        }
    },
    
    async login(email, password) {
        const data = await api.login(email, password);
        this.token = data.token;
        api.setToken(this.token);
        await this.fetchMe();
        return data;
    },
    
    async signup(email, password, displayName) {
        const data = await api.signup(email, password, displayName);
        this.token = data.token;
        api.setToken(this.token);
        await this.fetchMe();
        return data;
    },
    
    logout() {
        this.token = null;
        this.user = null;
        api.setToken(null);
        this.updateAuthUI();
        window.location.href = '/login';
    }
};

// Page-specific initialization
const pages = {
    // Home Dashboard
    home: {
        refreshTimer: null,
        inFlightRefresh: null,
        
        async init() {
            if (!authState.user) return;
            await this.loadWallet();
            await this.loadActivity();
            this.bindEvents();
            this.startAutoRefresh();
        },
        
        async loadWallet() {
            const refreshId = Date.now();
            this.currentRefreshId = refreshId;

            try {
                const data = await api.me();

                // Ignore stale responses
                if (this.currentRefreshId !== refreshId) {
                    console.log('Ignoring stale wallet response');
                    return;
                }

                const balanceEl = document.getElementById('wallet-balance');
                const availableEl = document.getElementById('wallet-available');
                const oldBalance = balanceEl ? parseInt(balanceEl.dataset.minor || '0') : null;
                const oldAvailable = availableEl ? parseInt(availableEl.dataset.minor || '0') : null;

                document.getElementById('wallet-balance').textContent = formatMinorUnits(data.balance);
                document.getElementById('wallet-balance-minor').value = data.balance;
                balanceEl?.setAttribute('data-minor', data.balance);
                document.getElementById('wallet-available').textContent = formatMinorUnits(data.available);
                document.getElementById('wallet-available-minor').value = data.available;
                availableEl?.setAttribute('data-minor', data.available);

                // Announce balance change to screen readers
                if (oldBalance !== null) {
                    const balanceChange = data.balance - oldBalance;
                    if (balanceChange !== 0) {
                        const direction = balanceChange > 0 ? 'added' : 'reduced';
                        announce(`${formatMinorUnits(Math.abs(balanceChange))} EUR ${direction} to your balance`);
                    }
                }

                const heldEl = document.getElementById('wallet-held');
                const heldContainer = heldEl?.parentElement?.parentElement;
                if (data.held > 0) {
                    heldEl.textContent = formatMinorUnits(data.held);
                    document.getElementById('wallet-held-minor').value = data.held;
                    if (heldContainer) heldContainer.style.display = 'block';
                } else if (heldContainer) {
                    heldContainer.style.display = 'none';
                }
            } catch (e) {
                console.error('Failed to load wallet:', e);
            }
        },
        
        async loadActivity() {
            try {
                const [paymentsData, authsData] = await Promise.all([
                    api.getActivity(50, 0),
                    api.listAuthorizations(null, null, 50, 0)
                ]);
                const list = document.getElementById('activity-list');
                const empty = document.querySelector('.empty-activity');
                
                // Combine payments and authorizations
                const allItems = [...paymentsData.payments, ...authsData.authorizations];
                
                if (allItems.length === 0) {
                    list.innerHTML = '';
                    if (empty) empty.style.display = 'block';
                    // Announce empty state
                    announce('No activity');
                    return;
                }
                
                if (empty) empty.style.display = 'none';
                
                list.innerHTML = allItems.map(item => {
                    // Handle payment items
                    if (item.payment_id) {
                        const p = item;
                        const isOutgoing = p.from_user_id === authState.user?.user_id;
                        const amountClass = isOutgoing ? 'style="color: var(--negative)"' : 'style="color: var(--positive)"';
                        const sign = isOutgoing ? '-' : '+';
                        const visibilityIcon = p.visibility === 'public' ? '🌐' : '🔒';
                        
                        return `
                            <div class="activity-item" id="activity-item-${p.payment_id}" data-visibility="${p.visibility}" role="listitem" aria-label="${isOutgoing ? 'Outgoing payment to ' + p.to_handle : 'Incoming payment from ' + p.from_handle}${p.note ? ': ' + p.note : ''}">
                                <div class="activity-parties">
                                    <strong>${p.from_handle}</strong> ${isOutgoing ? '→' : '←'} <strong>${p.to_handle}</strong>
                                </div>
                                <div class="activity-amount" ${amountClass}>${sign}${formatMinorUnits(p.amount)}</div>
                                <div class="activity-note">${p.note || ''} ${visibilityIcon}</div>
                            </div>
                        `;
                    }
                    // Handle authorization items
                    else if (item.id) {
                        const auth = item;
                        const isIncoming = auth.to_user_id === authState.user?.user_id;
                        const otherParty = isIncoming ? auth.from_handle : auth.to_handle;
                        const amountClass = isIncoming ? 'style="color: var(--positive)"' : 'style="color: var(--negative)"';
                        const sign = isIncoming ? '+' : '-';
                        
                        let actions = '';
                        if (auth.status === 'open') {
                            if (isIncoming) {
                                actions = `<button class="btn btn-success btn-sm" data-action="capture" data-auth-id="${auth.id}" data-remaining="${auth.amount - auth.captured_amount}" aria-label="Capture ${auth.amount - auth.captured_amount} from authorization">${auth.amount - auth.captured_amount > 0 ? 'Capture' : 'Captured'}</button>`;
                            } else {
                                actions = `<button class="btn btn-danger btn-sm" data-action="void" data-auth-id="${auth.id}" aria-label="Void authorization">${auth.id > 0 ? 'Void' : 'Voided'}</button>`;
                            }
                        } else if (auth.status === 'captured') {
                            actions = `<span style="color: var(--text-secondary)" aria-label="Captured">${auth.status}</span>`;
                        } else if (auth.status === 'voided') {
                            actions = `<span style="color: var(--text-secondary)" aria-label="Voided">${auth.status}</span>`;
                        } else if (auth.status === 'expired') {
                            actions = `<span style="color: var(--text-secondary)" aria-label="Expired">${auth.status}</span>`;
                        }
                        
                        return `
                            <div class="activity-item" id="activity-item-${auth.id}" data-visibility="${auth.visibility}" data-status="${auth.status}" role="listitem" aria-label="${isIncoming ? 'Incoming authorization from ' + otherParty : 'Outgoing authorization to ' + otherParty} ${auth.status}${auth.note ? ': ' + auth.note : ''}">
                                <div class="activity-parties">
                                    <strong>${otherParty}</strong> ${isIncoming ? '→' : '←'} <strong>${isIncoming ? auth.to_handle : auth.from_handle}</strong>
                                </div>
                                <div class="activity-amount" ${amountClass}>${sign}${formatMinorUnits(auth.amount)}</div>
                                <div class="activity-note">${auth.note || ''}</div>
                                <div class="activity-details tiny">${auth.status}: ${auth.captured_amount}/${auth.amount} captured</div>
                            </div>
                        `;
                    }
                    return '';
                }).join('');
                
                // Bind action buttons after rendering
                setTimeout(() => {
                    list.querySelectorAll('[data-action]').forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            const action = btn.dataset.action;
                            const authId = btn.dataset.authId;
                            this.handleActivityAuthAction(action, authId, btn);
                        });
                    });
                }, 100);
                
                // Announce number of new items
                announce(`Loaded ${allItems.length} activity items`);
            } catch (e) {
                console.error('Failed to load activity:', e);
            }
        },
        
        bindEvents() {
            // Pay form
            const payForm = document.querySelector('#pay-submit')?.parentElement;
            if (payForm) {
                document.getElementById('pay-submit').addEventListener('click', async (e) => {
                    e.preventDefault();
                    await this.handlePay();
                });
            }
            
            // Request form
            const requestForm = document.querySelector('#request-submit')?.parentElement;
            if (requestForm) {
                document.getElementById('request-submit').addEventListener('click', async (e) => {
                    e.preventDefault();
                    await this.handleRequest();
                });
            }
            
            // Wallet refresh
            const refreshBtn = document.getElementById('wallet-refresh');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => this.refreshWallet());
            }
        },
        
        async handlePay() {
            const handle = document.getElementById('pay-handle').value.trim();
            const amountStr = document.getElementById('pay-amount').value.trim();
            const note = document.getElementById('pay-note').value.trim();
            const visibility = document.getElementById('pay-visibility').value;
            
            if (!handle || !amountStr) {
                showError('pay-error', 'Handle and amount are required');
                return;
            }
            
            hideError('pay-error');
            hideUncertain('pay-uncertain');
            setLoading('pay-submit', true);
            
            try {
                const amount = parseAmount(amountStr);
                await api.pay(handle, amount, note, visibility);
                // Clear form but preserve values per spec
                document.getElementById('pay-amount').value = '';
                document.getElementById('pay-note').value = '';
                await this.loadWallet();
                await this.loadActivity();
            } catch (e) {
                if (e.code === 'network_error' || e.status === 0) {
                    showUncertain('pay-uncertain', 'Payment may have succeeded. Retrying...');
                    // Retry with same idempotency key would need stored key
                } else {
                    showError('pay-error', e.message);
                }
            } finally {
                setLoading('pay-submit', false);
            }
        },
        
        async handlePayWithIdempotency() {
            const handle = document.getElementById('pay-handle').value.trim();
            const amountStr = document.getElementById('pay-amount').value.trim();
            const note = document.getElementById('pay-note').value.trim();
            const visibility = document.getElementById('pay-visibility').value;
            
            if (!handle || !amountStr) {
                showError('pay-error', 'Handle and amount are required');
                return;
            }
            
            hideError('pay-error');
            hideUncertain('pay-uncertain');
            setLoading('pay-submit', true);
            
            const idempotencyKey = document.getElementById('pay-ic-key')?.value || this.generateIdempotencyKey();
            
            try {
                const amount = parseAmount(amountStr);
                await api.pay(handle, amount, note, visibility, idempotencyKey);
                // Clear form but preserve values per spec
                document.getElementById('pay-amount').value = '';
                document.getElementById('pay-note').value = '';
                await this.loadWallet();
                await this.loadActivity();
            } catch (e) {
                if (e.code === 'network_error' || e.status === 0) {
                    showUncertain('pay-uncertain', 'Payment may have succeeded. Retrying...');
                } else {
                    showError('pay-error', e.message);
                }
            } finally {
                setLoading('pay-submit', false);
            }
        },
        
        async handleActivityAuthAction(action, authId, button) {
            const errorEl = document.getElementById(`authorization-error-${authId}`);
            const showError = (msg) => {
                if (errorEl) {
                    errorEl.textContent = msg;
                    errorEl.style.display = 'block';
                }
            };
            const hideError = () => {
                if (errorEl) {
                    errorEl.style.display = 'none';
                    errorEl.textContent = '';
                }
            };
            
            hideError();
            setLoading(button.id, true);
            
            try {
                if (action === 'void') {
                    api.voidAuthorization(authId);
                } else if (action === 'capture') {
                    const amount = parseInt(button.dataset.amount);
                    const remaining = parseInt(button.dataset.remaining);
                    const final = remaining === amount;
                    api.captureAuthorization(authId, amount, final);
                }
                // Refresh activity and authorizations after action
                this.loadActivity();
                if (window.location.pathname === '/authorizations') {
                    pages.authorizations.init();
                }
            } catch (e) {
                showError(e.message);
            } finally {
                setLoading(button.id, false);
            }
        },
        
        // Handle authorization action with idempotency key
        handleAuthorizationActionWithIdempotency(action, authId, button, idempotencyKey) {
            const errorEl = document.getElementById(`authorization-error-${authId}`);
            const showError = (msg) => {
                if (errorEl) {
                    errorEl.textContent = msg;
                    errorEl.style.display = 'block';
                }
            };
            const hideError = () => {
                if (errorEl) {
                    errorEl.style.display = 'none';
                    errorEl.textContent = '';
                }
            };
            
            hideError();
            setLoading(button.id, true);
            
            try {
                if (action === 'void') {
                    api.voidAuthorization(authId, idempotencyKey);
                } else if (action === 'capture') {
                    const amount = parseInt(button.dataset.amount);
                    const remaining = parseInt(button.dataset.remaining);
                    const final = remaining === amount;
                    api.captureAuthorization(authId, amount, final, idempotencyKey);
                }
                // Refresh activity and authorizations after action
                this.loadActivity();
                if (window.location.pathname === '/authorizations') {
                    pages.authorizations.init();
                }
            } catch (e) {
                showError(e.message);
            } finally {
                setLoading(button.id, false);
            }
        },
        
        async handleRequest() {
            const handle = document.getElementById('request-handle').value.trim();
            const amountStr = document.getElementById('request-amount').value.trim();
            const note = document.getElementById('request-note').value.trim();
            
            if (!handle || !amountStr) {
                showError('request-error', 'Handle and amount are required');
                return;
            }
            
            hideError('request-error');
            setLoading('request-submit', true);
            
            try {
                const amount = parseAmount(amountStr);
                await api.request(handle, amount, note);
                document.getElementById('request-amount').value = '';
                document.getElementById('request-note').value = '';
            } catch (e) {
                showError('request-error', e.message);
            } finally {
                setLoading('request-submit', false);
            }
        },
        
        async refreshWallet() {
            // Cancel previous in-flight refresh (we'll ignore stale response)
            if (this.inFlightRefresh) {
                // We can't cancel the fetch, but we'll track the latest refresh
            }

            const refreshId = Date.now();
            this.inFlightRefresh = this.loadWallet();

            try {
                await this.inFlightRefresh;
            } catch (e) {
                console.error('Refresh failed:', e);
            } finally {
                // Only mark as complete if this is the latest refresh
                if (this.inFlightRefresh && this.inFlightRefresh._refreshId === refreshId) {
                    this.inFlightRefresh = null;
                }
            }
        },
        
        startAutoRefresh() {
            // Optional: auto-refresh every 30 seconds
            this.refreshTimer = setInterval(() => this.refreshWallet(), 30000);
        },
        
        destroy() {
            if (this.refreshTimer) clearInterval(this.refreshTimer);
        }
    },
    
    // Requests page
    requests: {
        async init() {
            if (!authState.user) return;
            await this.loadRequests();
            this.bindEvents();
        },
        
        async loadRequests() {
            try {
                const [incoming, outgoing] = await Promise.all([
                    api.listRequests('incoming', null),
                    api.listRequests('outgoing', null)
                ]);
                
                this.renderList('incoming', incoming.requests);
                this.renderList('outgoing', outgoing.requests);
            } catch (e) {
                console.error('Failed to load requests:', e);
            }
        },
        
        renderList(type, requests) {
            const listEl = document.getElementById(`${type}-list`);
            const emptyEl = document.getElementById(`${type}-list-empty`);
            
            if (!requests.length) {
                listEl.innerHTML = '';
                if (emptyEl) emptyEl.style.display = 'block';
                return;
            }
            
            if (emptyEl) emptyEl.style.display = 'none';
            
            listEl.innerHTML = requests.map(r => {
                const isIncoming = type === 'incoming';
                const otherParty = isIncoming ? r.requester_handle : r.payer_handle;
                const amountClass = isIncoming ? 'style="color: var(--positive)"' : 'style="color: var(--negative)"';
                const sign = isIncoming ? '+' : '-';
                
                let actions = '';
                if (r.status === 'pending') {
                    if (isIncoming) {
                        actions = `
                            <button class="btn btn-success" data-action="pay" data-request-id="${r.request_id}">Pay</button>
                            <button class="btn btn-danger" data-action="decline" data-request-id="${r.request_id}">Decline</button>
                        `;
                    } else {
                        actions = `
                            <button class="btn btn-secondary" data-action="cancel" data-request-id="${r.request_id}">Cancel</button>
                        `;
                    }
                } else if (r.status === 'paid') {
                    actions = `<span style="color: var(--positive)">Paid</span>`;
                } else if (r.status === 'declined') {
                    actions = `<span style="color: var(--negative)">Declined</span>`;
                } else if (r.status === 'cancelled') {
                    actions = `<span style="color: var(--text-secondary)">Cancelled</span>`;
                }
                
                return `
                    <div class="request-item" id="request-item-${r.request_id}" data-status="${r.status}">
                        <div class="request-amount" ${amountClass}>${sign}${formatMinorUnits(r.amount)}</div>
                        <div>From: ${r.requester_handle} → To: ${r.payer_handle}</div>
                        <div>${r.note || ''}</div>
                        <div>${actions}</div>
                        <div id="request-error-${r.request_id}" class="form-text" style="display: none; color: var(--negative);"></div>
                    </div>
                `;
            }).join('');
            
            // Bind action buttons
            listEl.querySelectorAll('[data-action]').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const action = btn.dataset.action;
                    const requestId = btn.dataset.requestId;
                    this.handleRequestAction(action, requestId);
                });
            });
        },
        
        async handleRequestAction(action, requestId) {
            const errorEl = document.getElementById(`request-error-${requestId}`);
            const showError = (msg) => {
                if (errorEl) {
                    errorEl.textContent = msg;
                    errorEl.style.display = 'block';
                }
            };
            const hideError = () => {
                if (errorEl) {
                    errorEl.style.display = 'none';
                    errorEl.textContent = '';
                }
            };
            
            hideError();
            
            try {
                if (action === 'pay') {
                    const visibility = 'private'; // default
                    await api.payRequest(requestId, visibility);
                } else if (action === 'decline') {
                    await api.declineRequest(requestId);
                } else if (action === 'cancel') {
                    await api.cancelRequest(requestId);
                }
                await this.loadRequests();
            } catch (e) {
                showError(e.message);
            }
        },
        
        bindEvents() {}
    },
    
    // Split page
    split: {
        previewTimer: null,
        
        async init() {
            if (!authState.user) return;
            this.bindEvents();
        },
        
        bindEvents() {
            const amountInput = document.getElementById('split-amount');
            const handlesInput = document.getElementById('split-handles');
            
            // Live preview
            const updatePreview = () => {
                clearTimeout(this.previewTimer);
                this.previewTimer = setTimeout(() => this.updatePreview(), 300);
            };
            
            amountInput?.addEventListener('input', updatePreview);
            handlesInput?.addEventListener('input', updatePreview);
            
            document.getElementById('split-submit')?.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.handleSplit();
            });
        },
        
        updatePreview() {
            const amountStr = document.getElementById('split-amount').value.trim();
            const handlesStr = document.getElementById('split-handles').value.trim();
            const preview = document.getElementById('split-preview');
            const empty = document.querySelector('.empty-splits');
            
            if (!amountStr || !handlesStr) {
                if (preview) preview.style.display = 'none';
                if (empty) empty.style.display = 'block';
                return;
            }
            
            try {
                const amount = parseAmount(amountStr);
                const handles = handlesStr.split(',').map(h => h.trim()).filter(h => h);
                
                if (handles.length === 0) throw new Error('No handles');
                
                const shares = this.calculateShares(amount, handles.length);
                
                if (preview) preview.style.display = 'block';
                if (empty) empty.style.display = 'none';
                
                handles.forEach((handle, i) => {
                    const el = document.getElementById(`share-${handle}`);
                    if (el) {
                        el.textContent = `${handle}: ${formatMinorUnits(shares[i])}`;
                    }
                });
            } catch (e) {
                if (preview) preview.style.display = 'none';
                if (empty) empty.style.display = 'block';
            }
        },
        
        calculateShares(amount, n) {
            const base = Math.floor(amount / n);
            const remainder = amount % n;
            return Array.from({ length: n }, (_, i) => base + (i < remainder ? 1 : 0));
        },
        
        async handleSplit() {
            const amountStr = document.getElementById('split-amount').value.trim();
            const handlesStr = document.getElementById('split-handles').value.trim();
            const note = document.getElementById('split-note').value.trim();
            
            if (!amountStr || !handlesStr) {
                showError('split-error', 'Amount and handles are required');
                return;
            }
            
            hideError('split-error');
            setLoading('split-submit', true);
            
            try {
                const amount = parseAmount(amountStr);
                const handles = handlesStr.split(',').map(h => h.trim()).filter(h => h);
                await api.createSplit(amount, handles, note);
                // Clear form
                document.getElementById('split-amount').value = '';
                document.getElementById('split-handles').value = '';
                document.getElementById('split-note').value = '';
                this.updatePreview();
            } catch (e) {
                showError('split-error', e.message);
            } finally {
                setLoading('split-submit', false);
            }
        }
    },
    
    // Authorizations page
    authorizations: {
        async init() {
            if (!authState.user) return;
            await this.loadAuthorizations();
            this.bindEvents();
        },

        async loadAuthorizations() {
            try {
                const data = await api.listAuthorizations(null, null, 50, 0);
                const listEl = document.getElementById('authorization-list');
                const emptyEl = document.querySelector('.empty-authorizations');

                if (!data.authorizations || data.authorizations.length === 0) {
                    listEl.innerHTML = '';
                    if (emptyEl) emptyEl.style.display = 'block';
                    return;
                }

                if (emptyEl) emptyEl.style.display = 'none';

                listEl.innerHTML = data.authorizations.map(auth => {
                    const isIncoming = auth.to_user_id === authState.user?.user_id;
                    const otherParty = isIncoming ? auth.from_handle : auth.to_handle;
                    const amountClass = isIncoming ? 'style="color: var(--positive)"' : 'style="color: var(--negative)"';
                    const sign = isIncoming ? '+' : '-';
                    const statusClass = this.getStatusClass(auth.status);
                    const remainingAmount = auth.amount - auth.captured_amount;

                    let actions = '';
                    if (auth.status === 'open') {
                        if (isIncoming) {
                            // Receiver can capture
                            actions = `
                                <button class="btn btn-success" data-action="capture" data-auth-id="${auth.id}" data-amount="${auth.amount}" data-remaining="${remainingAmount}" data-idempotency-key="${this.generateIdempotencyKey()}">Capture ${formatMinorUnits(remainingAmount)}</button>
                            `;
                        } else {
                            // Payer can void
                            actions = `
                                <button class="btn btn-danger" data-action="void" data-auth-id="${auth.id}" data-idempotency-key="${this.generateIdempotencyKey()}">Void</button>
                            `;
                        }
                    } else if (auth.status === 'captured') {
                        actions = `<span style="color: var(--text-secondary)">Captured</span>`;
                    } else if (auth.status === 'voided') {
                        actions = `<span style="color: var(--text-secondary)">Voided</span>`;
                    } else if (auth.status === 'expired') {
                        actions = `<span style="color: var(--text-secondary)">Expired</span>`;
                    }

                    return `
                        <div class="authorization-item" id="authorization-item-${auth.id}" data-testid="authorization-item-${auth.id}" data-status="${auth.status}">
                            <div class="authorization-header">
                                <div class="authorization-party">
                                    <strong>${otherParty}</strong>
                                    <span class="authorization-direction">${isIncoming ? '→' : '←'}</span>
                                    <strong>${isIncoming ? auth.to_handle : auth.from_handle}</strong>
                                </div>
                                <div class="authorization-status ${statusClass}">${auth.status.toUpperCase()}</div>
                            </div>
                            <div class="authorization-amount" ${amountClass}>${sign}${formatMinorUnits(auth.amount)}</div>
                            <div class="authorization-details">
                                <div>Captured: ${formatMinorUnits(auth.captured_amount)}</div>
                                <div>Remaining: ${formatMinorUnits(remainingAmount)}</div>
                                ${auth.note ? `<div>Note: ${auth.note}</div>` : ''}
                                ${auth.expires_at ? `<div>Expires: ${new Date(auth.expires_at).toLocaleString()}</div>` : ''}
                            </div>
                            <div class="authorization-actions">
                                ${actions}
                            </div>
                            <div id="authorization-error-${auth.id}" class="form-text" style="display: none; color: var(--negative);" data-testid="authorization-error-${auth.id}" role="alert" aria-live="polite"></div>
                        </div>
                    `;
                }).join('');

                // Bind action buttons with idempotency key support
                listEl.querySelectorAll('[data-action]').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const action = btn.dataset.action;
                        const authId = btn.dataset.authId;
                        // Get idempotency key from data attribute if provided, otherwise generate one
                        const idempotencyKey = btn.dataset.idempotencyKey || this.generateIdempotencyKey();
                        this.handleAuthorizationActionWithIdempotency(action, authId, btn, idempotencyKey);
                    });
                });
            } catch (e) {
                console.error('Failed to load authorizations:', e);
                showError('authorization-error', 'Failed to load authorizations');
            }
        },

        getStatusClass(status) {
            const classes = {
                'open': 'status-open',
                'captured': 'status-captured',
                'voided': 'status-voided',
                'expired': 'status-expired'
            };
            return classes[status] || '';
        },

        async handleAuthorizationAction(action, authId, button) {
            const errorEl = document.getElementById(`authorization-error-${authId}`);
            const showError = (msg) => {
                if (errorEl) {
                    errorEl.textContent = msg;
                    errorEl.style.display = 'block';
                }
            };
            const hideError = () => {
                if (errorEl) {
                    errorEl.style.display = 'none';
                    errorEl.textContent = '';
                }
            };

            hideError();
            setLoading(button.id, true);

            try {
                if (action === 'void') {
                    await api.voidAuthorization(authId);
                    announce('Authorization voided successfully');
                } else if (action === 'capture') {
                    const amount = parseInt(button.dataset.amount);
                    const remaining = parseInt(button.dataset.remaining);
                    const final = remaining === amount;
                    await api.captureAuthorization(authId, amount, final);
                    announce('Authorization captured successfully');
                }
                await this.loadAuthorizations();
            } catch (e) {
                showError(e.message);
            } finally {
                setLoading(button.id, false);
            }
        },

        bindEvents() {
            // Event handlers are bound in loadAuthorizations
        }
    },
    
    // Signup page
    signup: {
        init() {
            document.getElementById('signup-submit')?.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.handleSignup();
            });
        },
        
        async handleSignup() {
            const email = document.getElementById('signup-email').value.trim();
            const password = document.getElementById('signup-password').value;
            const displayName = document.getElementById('signup-display-name').value.trim();
            
            if (!email || !password || !displayName) {
                showError('auth-error', 'All fields are required');
                return;
            }
            
            hideError('auth-error');
            setLoading('signup-submit', true);
            
            try {
                await authState.signup(email, password, displayName);
                window.location.href = '/';
            } catch (e) {
                showError('auth-error', e.message);
            } finally {
                setLoading('signup-submit', false);
            }
        }
    },
    
    // Login page
    login: {
        init() {
            document.getElementById('login-submit')?.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.handleLogin();
            });
        },
        
        async handleLogin() {
            const email = document.getElementById('login-email').value.trim();
            const password = document.getElementById('login-password').value;
            
            if (!email || !password) {
                showError('auth-error', 'Email and password are required');
                return;
            }
            
            hideError('auth-error');
            setLoading('login-submit', true);
            
            try {
                await authState.login(email, password);
                window.location.href = '/';
            } catch (e) {
                showError('auth-error', e.message);
            } finally {
                setLoading('login-submit', false);
            }
        }
    }
};

// Global logout handler
document.addEventListener('click', (e) => {
    if (e.target.id === 'logout-button') {
        authState.logout();
    }
});

// Page detection and initialization
document.addEventListener('DOMContentLoaded', () => {
    // Store original button texts
    document.querySelectorAll('.btn').forEach(btn => {
        btn.dataset.originalText = btn.textContent;
    });
    
    authState.init();
    
    // Detect current page and initialize
    const path = window.location.pathname;
    
    if (path === '/' || path === '/index.html') {
        window.onAuthReady = () => pages.home.init();
    } else if (path === '/signup') {
        pages.signup.init();
    } else if (path === '/login') {
        pages.login.init();
    } else if (path === '/requests') {
        window.onAuthReady = () => pages.requests.init();
    } else if (path === '/split') {
        window.onAuthReady = () => pages.split.init();
    } else if (path === '/authorizations') {
        window.onAuthReady = () => pages.authorizations.init();
    }
    
    // If already authenticated, trigger ready
    if (authState.user) {
        if (window.onAuthReady) window.onAuthReady(authState.user);
    }
});