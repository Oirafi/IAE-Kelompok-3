const axios = require('axios');

// ─── Service URLs ────────────────────────────────────────────────────────────

const AUTH_URL = process.env.AUTH_SERVICE_URL || 'http://auth-service:3001';
const COURT_URL = process.env.COURT_SERVICE_URL || 'http://court-service:3002';
const BOOKING_URL = process.env.BOOKING_SERVICE_URL || 'http://booking-service:3003';
const EQUIPMENT_URL = process.env.EQUIPMENT_SERVICE_URL || 'http://equipment-service:3004';
const PAYMENT_URL = process.env.PAYMENT_SERVICE_URL || 'http://payment-service:3005/api';

// ─── Helper ──────────────────────────────────────────────────────────────────

function authHeaders(context) {
  return context.token ? { Authorization: context.token } : {};
}

// ─── Resolvers ───────────────────────────────────────────────────────────────

const resolvers = {

  // ═══════════════════════════════════════════════════════════════════════════
  // QUERIES
  // ═══════════════════════════════════════════════════════════════════════════

  Query: {

    // ─── Auth ──────────────────────────────────────────────────────────────
    profile: async (_, __, context) => {
      const { data } = await axios.get(`${AUTH_URL}/profile`, {
        headers: authHeaders(context),
      });
      return data;
    },

    // ─── Courts ────────────────────────────────────────────────────────────
    courts: async () => {
      const { data } = await axios.get(`${COURT_URL}/`);
      return data;
    },

    court: async (_, { id }) => {
      const { data } = await axios.get(`${COURT_URL}/${id}`);
      return data;
    },

    courtSchedule: async (_, { court_id }) => {
      const { data } = await axios.get(`${COURT_URL}/${court_id}/schedule`);
      return data;
    },

    // ─── Bookings ──────────────────────────────────────────────────────────
    bookings: async (_, __, context) => {
      const { data } = await axios.get(`${BOOKING_URL}/`, {
        headers: authHeaders(context),
      });
      return data;
    },

    booking: async (_, { id }, context) => {
      const { data } = await axios.get(`${BOOKING_URL}/${id}`, {
        headers: authHeaders(context),
      });
      return data;
    },

    // ─── Equipments ────────────────────────────────────────────────────────
    equipments: async () => {
      const { data } = await axios.get(`${EQUIPMENT_URL}/`);
      return data;
    },

    equipment: async (_, { id }) => {
      const { data } = await axios.get(`${EQUIPMENT_URL}/${id}`);
      return data;
    },

    cart: async (_, __, context) => {
      const { data } = await axios.get(`${EQUIPMENT_URL}/cart`, {
        headers: authHeaders(context),
      });
      return data;
    },

    // ─── Payments ──────────────────────────────────────────────────────────
    paymentStatus: async (_, { id }, context) => {
      const { data } = await axios.get(`${PAYMENT_URL}/status/${id}`, {
        headers: authHeaders(context),
      });
      return data;
    },
  },

  // ═══════════════════════════════════════════════════════════════════════════
  // MUTATIONS
  // ═══════════════════════════════════════════════════════════════════════════

  Mutation: {

    // ─── Auth ──────────────────────────────────────────────────────────────
    register: async (_, args) => {
      const { data } = await axios.post(`${AUTH_URL}/register`, args);
      return data;
    },

    login: async (_, args) => {
      const { data } = await axios.post(`${AUTH_URL}/login`, args);
      return data;
    },

    updateProfile: async (_, args, context) => {
      const { data } = await axios.put(`${AUTH_URL}/profile`, args, {
        headers: authHeaders(context),
      });
      return data;
    },

    // ─── Courts ────────────────────────────────────────────────────────────
    createCourt: async (_, args) => {
      const { data } = await axios.post(`${COURT_URL}/`, args);
      return data;
    },

    updateCourt: async (_, { id, ...updates }) => {
      const { data } = await axios.put(`${COURT_URL}/${id}`, updates);
      return data;
    },

    deleteCourt: async (_, { id }) => {
      const { data } = await axios.delete(`${COURT_URL}/${id}`);
      return data;
    },

    // ─── Bookings ──────────────────────────────────────────────────────────
    createBooking: async (_, args, context) => {
      const { data } = await axios.post(`${BOOKING_URL}/`, args, {
        headers: authHeaders(context),
      });
      return data;
    },

    deleteBooking: async (_, { id }, context) => {
      const { data } = await axios.delete(`${BOOKING_URL}/${id}`, {
        headers: authHeaders(context),
      });
      return data;
    },

    // ─── Equipments ────────────────────────────────────────────────────────
    createEquipment: async (_, args) => {
      const { data } = await axios.post(`${EQUIPMENT_URL}/`, args);
      return data;
    },

    updateEquipment: async (_, { id, ...updates }) => {
      const { data } = await axios.put(`${EQUIPMENT_URL}/${id}`, updates);
      return data;
    },

    deleteEquipment: async (_, { id }) => {
      const { data } = await axios.delete(`${EQUIPMENT_URL}/${id}`);
      return data;
    },

    addToCart: async (_, args, context) => {
      const { data } = await axios.post(`${EQUIPMENT_URL}/cart`, args, {
        headers: authHeaders(context),
      });
      return data;
    },

    removeFromCart: async (_, { cart_id }, context) => {
      const { data } = await axios.delete(`${EQUIPMENT_URL}/cart/${cart_id}`, {
        headers: authHeaders(context),
      });
      return data;
    },

    // ─── Payments ──────────────────────────────────────────────────────────
    createPayment: async (_, args, context) => {
      const { data } = await axios.post(`${PAYMENT_URL}/create`, args, {
        headers: authHeaders(context),
      });
      return data;
    },
  },
};

module.exports = resolvers;
