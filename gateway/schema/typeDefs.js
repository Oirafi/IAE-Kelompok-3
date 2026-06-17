const { gql } = require('graphql-tag');

const typeDefs = gql`
  # ─── Auth Types ──────────────────────────────────────────────────────────────

  type User {
    id: Int
    name: String
    email: String
    phone: String
    avatar: String
    google_id: String
    role: String
    created_at: String
    updated_at: String
  }

  type AuthResponse {
    message: String
    token: String
    user: User
  }

  # ─── Court Types ─────────────────────────────────────────────────────────────

  type Court {
    id: Int
    name: String
    description: String
    image: String
    price_per_hour: Int
    status: String
  }

  type CourtSchedule {
    id: Int
    court_id: Int
    day: String
    open_time: String
    close_time: String
  }

  # ─── Booking Types ──────────────────────────────────────────────────────────

  type BookingDetail {
    id: Int
    booking_id: Int
    court_id: Int
    start_time: String
    end_time: String
    duration: Int
  }

  type Booking {
    id: Int
    booking_code: String
    user_id: Int
    booking_date: String
    status: String
    total_price: Int
    details: [BookingDetail]
    created_at: String
    updated_at: String
  }

  type BookingResponse {
    message: String
    booking: Booking
  }

  # ─── Equipment Types ────────────────────────────────────────────────────────

  type Equipment {
    _id: String
    name: String
    image: String
    rental_price: Int
    stock: Int
  }

  type CartItem {
    _id: String
    user_id: Int
    equipment_id: String
    quantity: Int
    Equipment: Equipment
  }

  # ─── Payment Types ──────────────────────────────────────────────────────────

  type Transaction {
    id: Int
    booking_id: Int
    transaction_code: String
    snap_token: String
    total_payment: Int
    payment_status: String
    payment_type: String
    payment_time: String
    created_at: String
    updated_at: String
  }

  type PaymentResponse {
    message: String
    transaction_id: Int
    snap_token: String
    redirect_url: String
  }

  # ─── Generic Response ───────────────────────────────────────────────────────

  type MessageResponse {
    message: String
  }

  # ─── Queries ─────────────────────────────────────────────────────────────────

  type Query {
    # Auth
    profile: User

    # Courts
    courts: [Court]
    court(id: Int!): Court
    courtSchedule(court_id: Int!): [CourtSchedule]

    # Bookings
    bookings: [Booking]
    booking(id: Int!): Booking

    # Equipments
    equipments: [Equipment]
    equipment(id: String!): Equipment
    cart: [CartItem]

    # Payments
    paymentStatus(id: Int!): Transaction
  }

  # ─── Mutations ───────────────────────────────────────────────────────────────

  type Mutation {
    # Auth
    register(name: String!, email: String!, password: String!, phone: String): AuthResponse
    login(email: String!, password: String!): AuthResponse
    updateProfile(name: String, phone: String, avatar: String): MessageResponse

    # Courts
    createCourt(name: String!, description: String, image: String, price_per_hour: Int!, status: String): Court
    updateCourt(id: Int!, name: String, description: String, image: String, price_per_hour: Int, status: String): Court
    deleteCourt(id: Int!): MessageResponse

    # Bookings
    createBooking(court_id: Int!, booking_date: String!, start_time: String!, end_time: String!, duration: Int): BookingResponse
    deleteBooking(id: Int!): MessageResponse

    # Equipments
    createEquipment(name: String!, image: String, rental_price: Int!, stock: Int): Equipment
    updateEquipment(id: String!, name: String, image: String, rental_price: Int, stock: Int): Equipment
    deleteEquipment(id: String!): MessageResponse
    addToCart(equipment_id: String!, quantity: Int): CartItem
    removeFromCart(cart_id: String!): MessageResponse

    # Payments
    createPayment(booking_id: Int!): PaymentResponse
  }
`;

module.exports = typeDefs;
