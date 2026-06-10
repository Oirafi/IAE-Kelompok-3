const { Sequelize, DataTypes } = require('sequelize');
require('dotenv').config();

const sequelize = new Sequelize(
  process.env.DB_NAME || 'booking_db',
  process.env.DB_USER || 'root',
  process.env.DB_PASSWORD || 'root',
  {
    host: process.env.DB_HOST || 'mysql',
    dialect: 'mysql',
    logging: false,
  }
);

const Booking = sequelize.define('Booking', {
  id: { type: DataTypes.INTEGER, primaryKey: true, autoIncrement: true },
  booking_code: { type: DataTypes.STRING(50), allowNull: false, unique: true },
  user_id: { type: DataTypes.INTEGER, allowNull: false },
  booking_date: { type: DataTypes.DATEONLY, allowNull: false },
  status: { type: DataTypes.ENUM('pending', 'paid', 'cancelled'), defaultValue: 'pending' },
  total_price: { type: DataTypes.INTEGER, allowNull: false },
}, {
  tableName: 'bookings',
  timestamps: true,
  createdAt: 'created_at',
  updatedAt: 'updated_at'
});

const BookingDetail = sequelize.define('BookingDetail', {
  id: { type: DataTypes.INTEGER, primaryKey: true, autoIncrement: true },
  booking_id: { type: DataTypes.INTEGER, allowNull: false },
  court_id: { type: DataTypes.INTEGER, allowNull: false },
  start_time: { type: DataTypes.TIME, allowNull: false },
  end_time: { type: DataTypes.TIME, allowNull: false },
  duration: { type: DataTypes.INTEGER, allowNull: false }
}, {
  tableName: 'booking_details',
  timestamps: false
});

Booking.hasMany(BookingDetail, { foreignKey: 'booking_id', as: 'details', onDelete: 'CASCADE' });
BookingDetail.belongsTo(Booking, { foreignKey: 'booking_id' });

module.exports = { sequelize, Booking, BookingDetail };
