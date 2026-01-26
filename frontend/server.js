const path = require('path');
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const PORT = 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

const app = express();

// Serve static files from src
const srcDir = path.resolve(__dirname, '..', 'src');
app.use(express.static(srcDir));

// Proxy hotel API to backend to keep same-origin for frontend
app.use('/hotels', createProxyMiddleware({
  target: BACKEND_URL,
  changeOrigin: true,
  // Path rewrite: /hotels -> /hotels on backend
  pathRewrite: (pathStr) => pathStr,
  logLevel: 'warn',
}));

// Root -> home.html
app.get('/', (req, res) => {
  res.sendFile(path.join(srcDir, 'home.html'));
});

// Fallback for direct navigation to pages
app.get('/home', (req, res) => res.redirect('/'));
app.get('/search', (req, res) => res.sendFile(path.join(srcDir, 'search.html')));
app.get('/hotel-details', (req, res) => res.sendFile(path.join(srcDir, 'hotel-details.html')));

app.listen(PORT, () => {
  console.log(`Frontend server running on http://localhost:${PORT}`);
  console.log(`Proxying /hotels to ${BACKEND_URL}`);
});
