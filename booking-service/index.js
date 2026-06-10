const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const axios = require('axios');
const crypto = require('crypto');
const { sequelize, Booking, BookingDetail } = require('./models');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(express.json());

const COURT_SERVICE_URL = process.env.COURT_SERVICE_URL || 'http://court-service:3002';
const JWT_SECRET = process.env.JWT_SECRET || 'supersecretkey';

// JWT Middleware
const authenticate = (req, res, next) => {
    const authHeader = req.headers.authorization || '';
    const parts = authHeader.split(' ');
    if (parts.length !== 2 || parts[0].toLowerCase() !== 'bearer') {
        return res.status(401).json({ message: 'Access denied. No token provided.' });
    }
    try {
        const decoded = jwt.verify(parts[1], JWT_SECRET);
        req.user = decoded;
        next();
    } catch (error) {
        return res.status(401).json({ message: 'Invalid or expired token.' });
    }
};

app.get('/health', (req, res) => res.json({ status: 'OK', service: 'booking-service' }));

app.post('/', authenticate, async (req, res) => {
    const t = await sequelize.transaction();
    try {
        let { court_id, booking_date, start_time, end_time, duration } = req.body;
        const user_id = req.user.id;

        if (!duration && start_time && end_time) {
            const start = new Date(`1970-01-01T${start_time}Z`);
            const end = new Date(`1970-01-01T${end_time}Z`);
            duration = Math.floor((end - start) / 3600000);
        }

        // Check Court via API
        let court;
        try {
            const courtResp = await axios.get(`${COURT_SERVICE_URL}/${court_id}`, { timeout: 5000 });
            court = courtResp.data;
        } catch (error) {
            await t.rollback();
            if (error.response && error.response.status === 404) {
                return res.status(404).json({ message: 'Court not found' });
            }
            return res.status(503).json({ message: 'Failed to reach court service' });
        }

        // Check availability
        const existing = await BookingDetail.findOne({
            include: [{
                model: Booking,
                where: { booking_date, status: ['pending', 'paid'] }
            }],
            where: { court_id, start_time },
            transaction: t
        });

        if (existing) {
            await t.rollback();
            return res.status(400).json({ message: 'Court is not available for this time slot' });
        }

        const total_price = court.price_per_hour * duration;
        const booking_code = 'BKG-' + crypto.randomBytes(4).toString('hex').toUpperCase();

        const booking = await Booking.create({
            booking_code, user_id, booking_date, total_price, status: 'pending'
        }, { transaction: t });

        await BookingDetail.create({
            booking_id: booking.id, court_id, start_time, end_time, duration
        }, { transaction: t });

        await t.commit();
        const created = await Booking.findByPk(booking.id, { include: 'details' });
        return res.status(201).json({ message: 'Booking created successfully', booking: created });
    } catch (error) {
        await t.rollback();
        return res.status(500).json({ message: 'Server error', error: error.message });
    }
});

app.get('/', authenticate, async (req, res) => {
    try {
        const bookings = await Booking.findAll({ include: 'details' });
        return res.json(bookings);
    } catch (error) {
        return res.status(500).json({ message: 'Server error', error: error.message });
    }
});

app.get('/:id', authenticate, async (req, res) => {
    try {
        const booking = await Booking.findByPk(req.params.id, { include: 'details' });
        if (!booking) return res.status(404).json({ message: 'Booking not found' });
        return res.json(booking);
    } catch (error) {
        return res.status(500).json({ message: 'Server error', error: error.message });
    }
});

app.put('/:id', async (req, res) => {
    // No auth - internal from payment-service
    try {
        const booking = await Booking.findByPk(req.params.id);
        if (!booking) return res.status(404).json({ message: 'Booking not found' });
        booking.status = req.body.status;
        await booking.save();
        return res.json({ message: 'Booking status updated', booking });
    } catch (error) {
        return res.status(500).json({ message: 'Server error', error: error.message });
    }
});

app.delete('/:id', authenticate, async (req, res) => {
    try {
        const booking = await Booking.findByPk(req.params.id);
        if (!booking) return res.status(404).json({ message: 'Booking not found' });
        await booking.destroy();
        return res.json({ message: 'Booking deleted successfully' });
    } catch (error) {
        return res.status(500).json({ message: 'Server error', error: error.message });
    }
});

const PORT = process.env.PORT || 3003;

sequelize.sync().then(() => {
    console.log('Booking database synced');
    app.listen(PORT, () => console.log(`booking-service running on port ${PORT}`));
}).catch(err => console.error('DB Sync Error:', err));
