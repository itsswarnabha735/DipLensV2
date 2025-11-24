const yahooFinance = require('yahoo-finance2').default;
console.log('Default export:', yahooFinance);

try {
    yahooFinance.search('AAPL').then(res => console.log('Search result:', res)).catch(err => console.error('Search error:', err));
} catch (e) {
    console.error('Sync error:', e);
}
