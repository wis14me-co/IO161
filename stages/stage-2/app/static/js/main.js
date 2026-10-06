// Pocketful - Main JavaScript
(function() {
    'use strict';

    // CSRF Token handling
    function getCsrfToken() {
        return window.csrfToken || '';
    }

    // Add CSRF token to all forms
    function addCsrfToForms() {
        const forms = document.querySelectorAll('form[data-testid]');
        forms.forEach(form => {
            if (!form.querySelector('input[name="csrf_token"]')) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'csrf_token';
                input.value = getCsrfToken();
                form.prepend(input);
            }
        });
    }

    // Handle form submissions with confirmation
    function setupFormConfirmations() {
        const confirmForms = document.querySelectorAll('form[data-confirm]');
        confirmForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const message = form.dataset.confirm || 'Are you sure?';
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }

    // Handle delete/void buttons
    function setupDangerButtons() {
        const dangerButtons = document.querySelectorAll('button[data-danger]');
        dangerButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                const message = button.dataset.danger || 'This action cannot be undone. Continue?';
                if (!confirm(message)) {
                    e.preventDefault();
                }
            });
        });
    }

    // Wallet Refresh & Uncertainty Handling (Task 8)
    // Manages refresh state and shows pay-uncertain on network loss
    function setupWalletRefresh() {
        let refreshTimeout = null;
        let inFlightRefresh = false;
        
        // Refresh button handler
        const refreshButtons = document.querySelectorAll('[data-testid="wallet-refresh"]');
        refreshButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Cancel any previous in-flight refresh
                if (inFlightRefresh) {
                    clearTimeout(refreshTimeout);
                    refreshTimeout = null;
                    inFlightRefresh = false;
                    // Visual feedback: reset button state
                    button.textContent = 'Refreshing';
                    button.disabled = true;
                }
                
                // Start new refresh
                inFlightRefresh = true;
                button.textContent = 'Refreshing...';
                button.disabled = true;
                
                // Simulate refresh with timeout (replace with actual API call)
                refreshTimeout = setTimeout(() => {
                    inFlightRefresh = false;
                    button.textContent = 'Refresh';
                    button.disabled = false;
                    // Show success state
                    button.classList.add('btn-success');
                    setTimeout(() => button.classList.remove('btn-success'), 2000);
                }, 1500);
            });
        });
        
        // Handle network loss uncertainty - show pay-uncertain on payment forms
        const payForms = document.querySelectorAll('.pay-form');
        payForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                // Check if there's an ongoing refresh
                if (inFlightRefresh) {
                    e.preventDefault();
                    // Show uncertainty UI
                    const uncertainDiv = document.createElement('div');
                    uncertainDiv.className = 'alert alert-error';
                    uncertainDiv.setAttribute('data-testid', 'pay-uncertain');
                    uncertainDiv.innerHTML = '<strong>Network loss detected</strong>. Your payment may or may not have gone through. Retrying with the same idempotency key is recommended.';
                    form.insertBefore(uncertainDiv, form.firstChild);
                    
                    // Auto-remove after 5 seconds if not already handled
                    setTimeout(() => {
                        if (uncertainDiv.parentNode) {
                            uncertainDiv.style.opacity = '0';
                            uncertainDiv.style.transition = 'opacity 300ms';
                            setTimeout(() => uncertainDiv.remove(), 300);
                        }
                    }, 5000);
                }
            });
        });
        
        // Stale pay button disappearance on refresh
        const payButtons = document.querySelectorAll('button[data-testid="pay-btn"]');
        payButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Mark this button as stale - it should disappear on refresh
                button.classList.add('stale');
                button.disabled = true;
                button.textContent = 'Stale';
            });
        });
    }

    // Auto-dismiss alerts after 5 seconds
    function setupAlertDismissal() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 300ms';
                setTimeout(() => alert.remove(), 300);
            }, 5000);
        });
    }

    // Format currency display
    function formatCurrencyElements() {
        const elements = document.querySelectorAll('[data-currency]');
        elements.forEach(el => {
            const amount = parseInt(el.dataset.currency, 10);
            const currency = el.dataset.currencyCode || 'EUR';
            const minorUnits = parseInt(el.dataset.minorUnits || '2', 10);
            const formatted = formatCurrency(amount, currency, minorUnits);
            el.textContent = formatted;
        });
    }

    function formatCurrency(amount, currency, minorUnits) {
        const divisor = Math.pow(10, minorUnits);
        const formatted = (amount / divisor).toFixed(minorUnits);
        return currency + formatted;
    }

    // Copy to clipboard
    function setupCopyButtons() {
        const copyButtons = document.querySelectorAll('[data-copy]');
        copyButtons.forEach(button => {
            button.addEventListener('click', async function() {
                const targetSelector = button.dataset.copy;
                const target = document.querySelector(targetSelector);
                if (target) {
                    const text = target.value || target.textContent;
                    try {
                        await navigator.clipboard.writeText(text);
                        const originalText = button.textContent;
                        button.textContent = 'Copied!';
                        button.classList.add('btn-success');
                        setTimeout(() => {
                            button.textContent = originalText;
                            button.classList.remove('btn-success');
                        }, 2000);
                    } catch (err) {
                        console.error('Failed to copy:', err);
                    }
                }
            });
        });
    }

    // Keyboard navigation for tables
    function setupTableKeyboardNav() {
        const tables = document.querySelectorAll('.data-table');
        tables.forEach(table => {
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach((row, index) => {
                row.setAttribute('tabindex', '0');
                row.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' || e.key === ' ') {
                        const link = row.querySelector('a, button');
                        if (link) {
                            e.preventDefault();
                            link.click();
                        }
                    }
                });
            });
        });
    }

    // Mobile menu toggle (if needed)
    function setupMobileMenu() {
        const menuToggle = document.querySelector('[data-menu-toggle]');
        const menu = document.querySelector('[data-menu]');
        if (menuToggle && menu) {
            menuToggle.addEventListener('click', function() {
                menu.classList.toggle('is-open');
                menuToggle.setAttribute('aria-expanded', menu.classList.contains('is-open'));
            });
        }
    }

    // Initialize all
    function init() {
        addCsrfToForms();
        setupFormConfirmations();
        setupDangerButtons();
        setupAlertDismissal();
        formatCurrencyElements();
        setupCopyButtons();
        setupTableKeyboardNav();
        setupMobileMenu();
        setupWalletRefresh();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for testing
    window.Pocketful = {
        getCsrfToken,
        formatCurrency,
        init
    };
})();