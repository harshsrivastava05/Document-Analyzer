// frontend/src/lib/jwt.ts - Minimal fix
import jwt from 'jsonwebtoken';

export function createJWTForBackend(userId: string): string {
  const jwtSecret = process.env.JWT_SECRET || "fallback-insecure-secret-only-for-development-please-set-jwt-secret";
  
  const payload = {
    userId: userId,      // Changed from user_id to userId for consistency
    user_id: userId,     // Keep both for backward compatibility
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + (60 * 60 * 24), // 24 hours
  };

  return jwt.sign(payload, jwtSecret, { algorithm: 'HS256' });
}