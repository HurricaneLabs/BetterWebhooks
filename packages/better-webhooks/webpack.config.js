const fs = require('fs');
const path = require('path');
const CopyWebpackPlugin = require('copy-webpack-plugin');
const { merge: webpackMerge } = require('webpack-merge');
const baseConfig = require('@splunk/webpack-configs/base.config').default;

// bin/build.js sets NODE_ENV=production; `yarn start` (watch) leaves it unset.
const DEBUG = process.env.NODE_ENV !== 'production';

// Set up an entry config by iterating over the files in the pages directory.
const entries = fs
    .readdirSync(path.join(__dirname, 'src/main/webapp/pages'))
    .filter((pageFile) => !/^\./.test(pageFile))
    .reduce((accum, page) => {
        accum[page] = path.join(__dirname, 'src/main/webapp/pages', page);
        return accum;
    }, {});

module.exports = webpackMerge(baseConfig, {
    entry: entries,
    output: {
        path: path.join(__dirname, 'stage/appserver/static/pages/'),
        filename: '[name].js',
    },
    plugins: [
        new CopyWebpackPlugin({
            patterns: [
                {
                    from: path.join(__dirname, 'src/main/resources/splunk'),
                    to: path.join(__dirname, 'stage'),
                    // Compiled Python from local runs is a Splunkbase hard reject (#30).
                    globOptions: {
                        ignore: ['**/__pycache__/**', '**/*.pyc', '**/*.pyo'],
                    },
                },
            ],
        }),
    ],
    // Source maps only in watch builds: eval-source-map in the shipped bundle
    // wraps every module in eval() and keeps it unminified (@splunk/create 11.0.2).
    devtool: DEBUG ? 'eval-source-map' : false,
});
