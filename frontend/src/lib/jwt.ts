// frontend/src/lib/jwt.ts
import jwt from 'jsonwebtoken';

function getJWTSecret(): string {
  const jwtSecret = process.env.JWT_SECRET;
  
  if (!jwtSecret) {
    console.warn("⚠️ WARNING: JWT_SECRET not set! Using insecure fallback for development");
    return "fallback-insecure-secret-only-for-development-please-set-jwt-secret";
  }
  
  return jwtSecret;
}

export function createJWTForBackend(userId: string): string {
  const jwtSecret = getJWTSecret();
  
  const payload = {
    user_id: userId, 
    exp: Math.floor(Date.now() / 1000) + (60 * 60 * 24), 
    iat: Math.floor(Date.now() / 1000), 
  };

  console.log('🔑 Creating JWT token for user:', userId);
  
  try {
    const token = jwt.sign(payload, jwtSecret, { algorithm: 'HS256' });
    console.log('✅ JWT token created successfully');
    return token;
  } catch (error) {
    console.error('❌ Failed to create JWT token:', error);
    throw new Error('Failed to create authentication token');
  }
}

// Helper function to decode JWT (useful for debugging)
export function decodeJWT(token: string): any {
  try {
    return jwt.decode(token);
  } catch (error) {
    console.error('Failed to decode JWT:', error);
    return null;
  }
}