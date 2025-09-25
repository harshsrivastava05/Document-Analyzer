import jwt from 'jsonwebtoken';

export function createJWTForBackend(userId: string): string {
  const jwtSecret = process.env.JWT_SECRET || "fallback-insecure-secret-only-for-development-please-set-jwt-secret";
  
  const payload = {
    user_id: userId,
    exp: Math.floor(Date.now() / 1000) + (60 * 60 * 24), // 24 hours
  };

  return jwt.sign(payload, jwtSecret, { algorithm: 'HS256' });
}

