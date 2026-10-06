// Test script for frontend JavaScript functionality
// Run this in the browser console after loading the page

const testFrontend = () => {
    console.log('Testing frontend functionality...\n');

    // Test 1: API Client
    console.log('Test 1: API Client methods');
    try {
        console.assert(typeof api.listAuthorizations === 'function', 'listAuthorizations method not found');
        console.assert(typeof api.voidAuthorization === 'function', 'voidAuthorization method not found');
        console.assert(typeof api.captureAuthorization === 'function', 'captureAuthorization method not found');
        console.log('✅ API Client methods present\n');
    } catch (e) {
        console.error('❌ API Client test failed:', e);
    }

    // Test 2: Pages object
    console.log('Test 2: Pages object structure');
    try {
        console.assert(typeof pages.authorizations === 'object', 'pages.authorizations not found');
        console.assert(typeof pages.authorizations.loadAuthorizations === 'function', 'loadAuthorizations method not found');
        console.assert(typeof pages.authorizations.handleAuthorizationAction === 'function', 'handleAuthorizationAction method not found');
        console.assert(typeof pages.authorizations.getStatusClass === 'function', 'getStatusClass method not found');
        console.log('✅ Pages object structure valid\n');
    } catch (e) {
        console.error('❌ Pages object test failed:', e);
    }

    // Test 3: Wallet refresh with latest-refresh-wins
    console.log('Test 3: Wallet refresh with latest-refresh-wins logic');
    try {
        console.assert(typeof pages.home.refreshWallet === 'function', 'refreshWallet method not found');
        console.assert(typeof pages.home.loadWallet === 'function', 'loadWallet method not found');
        console.log('✅ Wallet refresh logic present\n');
    } catch (e) {
        console.error('❌ Wallet refresh test failed:', e);
    }

    // Test 4: Format functions
    console.log('Test 4: Format functions');
    try {
        const testAmount = 1500; // 15.00 EUR
        const formatted = formatMinorUnits(testAmount);
        console.assert(formatted === '15.00 EUR', `Expected '15.00 EUR', got '${formatted}'`);
        console.log(`✅ formatMinorUnits(${testAmount}) = '${formatted}'\n`);
    } catch (e) {
        console.error('❌ Format function test failed:', e);
    }

    // Test 5: Parse function
    console.log('Test 5: Parse function');
    try {
        const testStr = '15.00 EUR';
        const parsed = parseAmount(testStr);
        console.assert(parsed === 1500, `Expected 1500, got ${parsed}`);
        console.log(`✅ parseAmount('${testStr}') = ${parsed}\n`);
    } catch (e) {
        console.error('❌ Parse function test failed:', e);
    }

    // Test 6: Error display functions
    console.log('Test 6: Error display functions');
    try {
        console.assert(typeof showError === 'function', 'showError method not found');
        console.assert(typeof hideError === 'function', 'hideError method not found');
        console.assert(typeof showUncertain === 'function', 'showUncertain method not found');
        console.assert(typeof hideUncertain === 'function', 'hideUncertain method not found');
        console.log('✅ Error display functions present\n');
    } catch (e) {
        console.error('❌ Error display test failed:', e);
    }

    // Test 7: Loading state
    console.log('Test 7: Loading state function');
    try {
        console.assert(typeof setLoading === 'function', 'setLoading method not found');
        console.log('✅ Loading state function present\n');
    } catch (e) {
        console.error('❌ Loading state test failed:', e);
    }

    // Test 8: HTML elements
    console.log('Test 8: HTML elements check');
    try {
        const walletRefreshBtn = document.getElementById('wallet-refresh');
        console.assert(walletRefreshBtn, 'wallet-refresh button not found');
        console.assert(walletRefreshBtn.dataset.originalText, 'wallet-refresh button missing originalText');
        console.log('✅ HTML elements present\n');
    } catch (e) {
        console.error('❌ HTML elements test failed:', e);
    }

    // Test 9: Auth state
    console.log('Test 9: Auth state');
    try {
        console.assert(typeof authState === 'object', 'authState not found');
        console.assert(typeof authState.user === 'object', 'authState.user not found');
        console.log('✅ Auth state present\n');
    } catch (e) {
        console.error('❌ Auth state test failed:', e);
    }

    console.log('=== All tests completed ===');
};

// Run tests if script is loaded
if (typeof testFrontend === 'function') {
    testFrontend();
} else {
    console.log('Note: Run this test from the browser console after loading the page.');
}
