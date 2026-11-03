module.exports = {
    testMatch: ['**/*.unit.[jt]s?(x)'],
    // jest 27+ defaults to the node environment; the React tests need a DOM.
    testEnvironment: 'jsdom',
};
