<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\DB;
use Midtrans\Snap;
use Midtrans\Config;
use Midtrans\Transaction as MidtransTransaction;

class PaymentController extends Controller
{
    public function __construct()
    {
        Config::$serverKey = env('MIDTRANS_SERVER_KEY');
        Config::$isProduction = false;
        Config::$isSanitized = true;
        Config::$is3ds = true;
    }

    public function health()
    {
        return response()->json(['status' => 'OK', 'service' => 'payment-service']);
    }

    public function createPayment(Request $request)
    {
        $bookingId = $request->input('booking_id');
        $bookingUrl = env('BOOKING_SERVICE_URL', 'http://booking-service:3003');
        $token = $request->bearerToken();

        try {
            $bookingResp = Http::withToken($token)->get("{$bookingUrl}/{$bookingId}");
            if ($bookingResp->status() === 404) {
                return response()->json(['message' => 'Booking not found'], 404);
            }
            if (!$bookingResp->successful()) {
                return response()->json(['message' => 'Failed to reach booking service'], 503);
            }
            $booking = $bookingResp->json();
        } catch (\Exception $e) {
            return response()->json(['message' => 'Failed to reach booking service'], 503);
        }

        $transactionCode = "TRX-{$booking['booking_code']}-" . time();

        try {
            $params = [
                'transaction_details' => [
                    'order_id' => $transactionCode,
                    'gross_amount' => $booking['total_price'],
                ],
                'customer_details' => [
                    'first_name' => 'User',
                    'email' => 'user@example.com',
                ]
            ];

            $snapResponse = Snap::createTransaction($params);

            $transactionId = DB::table('transactions')->insertGetId([
                'booking_id' => $bookingId,
                'transaction_code' => $transactionCode,
                'snap_token' => $snapResponse->token,
                'total_payment' => $booking['total_price'],
                'payment_status' => 'pending',
                'created_at' => now(),
                'updated_at' => now(),
            ]);

            return response()->json([
                'message' => 'Payment transaction created',
                'transaction_id' => $transactionId,
                'snap_token' => $snapResponse->token,
                'redirect_url' => $snapResponse->redirect_url
            ], 201);
        } catch (\Exception $e) {
            return response()->json(['message' => 'Server error', 'error' => $e->getMessage()], 500);
        }
    }

    public function callback(Request $request)
    {
        try {
            $notification = $request->all();
            
            $statusResponse = MidtransTransaction::status($notification['order_id']);

            $orderId = $statusResponse->order_id;
            $transactionStatus = $statusResponse->transaction_status;
            $paymentType = $statusResponse->payment_type;
            $settlementTime = $statusResponse->settlement_time ?? null;

            $transaction = DB::table('transactions')->where('transaction_code', $orderId)->first();
            if (!$transaction) {
                return response()->json(['message' => 'Transaction not found'], 404);
            }

            DB::table('transactions')->where('transaction_code', $orderId)->update([
                'payment_status' => $transactionStatus,
                'payment_type' => $paymentType,
                'payment_time' => $settlementTime,
                'updated_at' => now(),
            ]);

            $bookingUrl = env('BOOKING_SERVICE_URL', 'http://booking-service:3003');

            if (in_array($transactionStatus, ['settlement', 'capture'])) {
                Http::put("{$bookingUrl}/{$transaction->booking_id}", ['status' => 'paid']);
            } elseif (in_array($transactionStatus, ['cancel', 'expire', 'deny'])) {
                Http::put("{$bookingUrl}/{$transaction->booking_id}", ['status' => 'cancelled']);
            }

            return response()->json(['message' => 'Callback processed']);
        } catch (\Exception $e) {
            return response()->json(['message' => 'Server error', 'error' => $e->getMessage()], 500);
        }
    }

    public function getStatus($id)
    {
        $transaction = DB::table('transactions')->where('id', $id)->first();
        if (!$transaction) {
            return response()->json(['message' => 'Transaction not found'], 404);
        }
        return response()->json($transaction);
    }
}
