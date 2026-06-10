<?php

namespace App\Http\Middleware;

use Closure;
use Exception;
use Illuminate\Http\Request;
use Firebase\JWT\JWT;
use Firebase\JWT\Key;

class JwtMiddleware
{
    public function handle(Request $request, Closure $next)
    {
        $header = $request->header('Authorization');
        if (!$header || !preg_match('/Bearer\s(\S+)/', $header, $matches)) {
            return response()->json(['message' => 'Access denied. No token provided.'], 401);
        }

        $token = $matches[1];
        try {
            $secret = env('JWT_SECRET', 'supersecretkey_supersecretkey_32');
            $decoded = JWT::decode($token, new Key($secret, 'HS256'));
            // Attach user data to request
            $request->merge(['user' => (array) $decoded]);
        } catch (Exception $e) {
            return response()->json(['message' => 'Invalid or expired token.', 'error' => $e->getMessage()], 401);
        }

        return $next($request);
    }
}
