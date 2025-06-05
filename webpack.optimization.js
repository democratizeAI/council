
// webpack.config.js optimization
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\/]node_modules[\/]/,
          name: 'vendors',
          chunks: 'all',
        },
        chat: {
          test: /[\/]src[\/]chat[\/]/,
          name: 'chat',
          chunks: 'all',
        }
      }
    }
  },
  resolve: {
    alias: {
      // Tree-shake lodash
      'lodash': 'lodash-es'
    }
  }
};
