const YahooFinance = require('yahoo-finance2').default;
try {
    const yahooFinance = new YahooFinance();
    console.log('Instance created');
    yahooFinance.search('AAPL').then(res => console.log('Search result:', res)).catch(err => console.error('Search error:', err));
} catch (e) {
    console.error('Instantiation error:', e);
}
