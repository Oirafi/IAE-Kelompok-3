<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up()
    {
        Schema::create('transactions', function (Blueprint $table) {
            $table->id();
            $table->integer('booking_id');
            $table->string('transaction_code', 50)->unique();
            $table->string('snap_token', 255)->nullable();
            $table->integer('total_payment');
            $table->string('payment_status', 20)->default('pending');
            $table->string('payment_type', 50)->nullable();
            $table->timestamp('payment_time')->nullable();
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('transactions');
    }
};
