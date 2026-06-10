<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\PaymentController;
use App\Http\Middleware\JwtMiddleware;

Route::get('/health', [PaymentController::class, 'health']);
Route::post('/callback', [PaymentController::class, 'callback']);

Route::middleware([JwtMiddleware::class])->group(function () {
    Route::post('/create', [PaymentController::class, 'createPayment']);
    Route::get('/status/{id}', [PaymentController::class, 'getStatus']);
});
