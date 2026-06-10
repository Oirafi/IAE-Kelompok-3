const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
require('dotenv').config();

const app = express();
app.use(cors());

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'Gateway OK' });
});

// Proxy rules
const services = {
    '/api/auth': process.env.AUTH_SERVICE_URL || 'http://auth-service:3001',
    '/api/courts': process.env.COURT_SERVICE_URL || 'http://court-service:3002',
    '/api/bookings': process.env.BOOKING_SERVICE_URL || 'http://booking-service:3003',
    '/api/equipments': process.env.EQUIPMENT_SERVICE_URL || 'http://equipment-service:3004',
    '/api/payments': process.env.PAYMENT_SERVICE_URL || 'http://payment-service:3005/api'
};

for (const [prefix, target] of Object.entries(services)) {
    app.use(prefix, createProxyMiddleware({
        target: target,
        changeOrigin: true,
        pathRewrite: {
            [`^${prefix}`]: '', // strip prefix
        },
    }));
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`API Gateway running on port ${PORT}`);
});
