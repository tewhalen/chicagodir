const path = require('path');
const webpack = require('webpack');

/*
 * Webpack Plugins
 */
const MiniCssExtractPlugin = require('mini-css-extract-plugin');

const ProductionPlugins = [
  // production webpack plugins go here
  new webpack.DefinePlugin({
    "process.env": {
      NODE_ENV: JSON.stringify("production")
    }
  })
]

const debug = process.env.NODE_ENV === 'production' ? 'production' : 'development';
const rootAssetPath = path.join(__dirname, 'assets');

module.exports = {
  // configuration
  context: __dirname,
  entry: {
    main_js: './assets/js/main',
    main_css: [
      path.join(__dirname, 'node_modules', '@fortawesome', 'fontawesome-free', 'css', 'all.css'),
      path.join(__dirname, 'node_modules', 'bootstrap', 'dist', 'css', 'bootstrap.css'),
      path.join(__dirname, 'assets', 'css', 'style.css'),
    ],
  },
  mode: debug,
  output: {
    chunkFilename: "[id].js",
    filename: "[name].bundle.js",
    path: path.join(__dirname, "chicagodir", "static", "build"),
    publicPath: "/static/build/",
    assetModuleFilename: "[path][name][ext][query]",
  },
  resolve: {
    extensions: [".js", ".jsx", ".css"]
  },
  devtool: debug ? "eval-source-map" : false,
  plugins: [
    new MiniCssExtractPlugin({ filename: "[name].bundle.css" }),
    new webpack.ProvidePlugin({ $: "jquery", jQuery: "jquery" })
  ].concat(debug ? [] : ProductionPlugins),
  module: {
    rules: [
      {
        test: /\.less$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
            options: {
            },
          },
          'css-loader!less-loader',
        ],
      },
      {
        test: /\.css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
            options: {
            },
          },
          'css-loader',
        ],
      },
      { test: /\.html$/, type: 'asset' },
      { test: /\.woff(2)?(\?v=[0-9]\.[0-9]\.[0-9])?$/, type: 'asset' },
      {
        test: /\.(ttf|eot|svg|png|jpe?g|gif|ico)(\?.*)?$/i,
        type: 'asset'
      },
      { test: /\.js$/, exclude: /node_modules/, loader: 'babel-loader', options: { presets: ["@babel/preset-env"], cacheDirectory: true } },
    ],
  }
};
