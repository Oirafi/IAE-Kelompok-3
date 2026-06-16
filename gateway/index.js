const express = require('express');
const cors = require('cors');
const { createProxyMiddleware } = require('http-proxy-middleware');
const { ApolloServer } = require('@apollo/server');
const { expressMiddleware } = require('@apollo/server/express4');
const typeDefs = require('./schema/typeDefs');
const resolvers = require('./schema/resolvers');
require('dotenv').config();

const app = express();
app.use(cors());

// ─── Health Check ─────────────────────────────────────────────────────────────

app.get('/health', (req, res) => {
    res.json({ status: 'Gateway OK' });
});

// ─── REST Proxy (backward compatible) ─────────────────────────────────────────

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

// ─── GraphQL (Apollo Server) ──────────────────────────────────────────────────

async function startApolloServer() {
    const server = new ApolloServer({
        typeDefs,
        resolvers,
        formatError: (error) => {
            console.error('GraphQL Error:', error.message);
            return {
                message: error.message,
                path: error.path,
            };
        },
    });

    await server.start();

    app.use(
        '/graphql',
        express.json(),
        expressMiddleware(server, {
            context: async ({ req }) => ({
                token: req.headers.authorization || '',
            }),
        })
    );

    const PORT = process.env.PORT || 3000;
    app.listen(PORT, () => {
        console.log(`API Gateway running on port ${PORT}`);
        console.log(`GraphQL endpoint: http://localhost:${PORT}/graphql`);
    });
}

startApolloServer().catch((err) => {
    console.error('Failed to start Apollo Server:', err);
    process.exit(1);
});
