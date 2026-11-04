module.exports = {
    extends: '@splunk/eslint-config/browser-prettier',
    overrides: [
        {
            // Unit tests run under jest on node: jest supplies describe/it/expect/jest,
            // node supplies `global` (the tests stub global.fetch).
            files: ['*.unit.jsx'],
            env: { jest: true, node: true },
        },
    ],
};
