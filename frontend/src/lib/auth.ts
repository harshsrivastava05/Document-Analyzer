// Update frontend/src/lib/auth.ts with better user ID handling

import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import { prisma } from "@/lib/prisma"

export const { auth, handlers, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
      allowDangerousEmailAccountLinking: true,
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, 
  },
  pages: {
    signIn: "/login",
    error: "/error",
  },
  callbacks: {
    async jwt({ token, account, user }) {
      // On first sign in, user and account will be present
      if (account && user) {
        console.log('🔍 JWT Callback - Initial sign in');
        console.log('🔍 User from OAuth:', { id: user.id, email: user.email });
        
        // For Google OAuth, use a consistent user ID format
        // Google sometimes returns different ID formats, so we'll use email as the key
        const consistentUserId = user.email ? `google_${user.email.replace(/[^a-zA-Z0-9]/g, '_')}` : user.id;
        
        token.userId = consistentUserId;
        token.email = user.email;
        token.name = user.name;
        token.image = user.image;
        
        console.log('🔍 JWT Callback - Consistent user ID:', consistentUserId);
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client
      if (token.userId) {
        session.user.id = token.userId as string;
      }
      if (token.email) {
        session.user.email = token.email as string;
      }
      if (token.name) {
        session.user.name = token.name as string;
      }
      if (token.image) {
        session.user.image = token.image as string;
      }
      
      console.log('🔍 Session Callback - Final user ID:', session.user.id);
      return session;
    },
  },
  events: {
    async signIn({ user, account }) {
      if (account?.provider === "google" && user.email) {
        try {
          // Use the same consistent user ID format as in JWT callback
          const consistentUserId = `google_${user.email.replace(/[^a-zA-Z0-9]/g, '_')}`;
          
          console.log('🔍 SignIn Event - Creating/updating user');
          console.log('🔍 Original Google ID:', user.id);
          console.log('🔍 Consistent ID:', consistentUserId);
          console.log('🔍 Email:', user.email);
          
          // Ensure user exists in database with consistent ID
          const dbUser = await prisma.user.upsert({
            where: { 
              email: user.email 
            },
            update: {
              name: user.name,
              image: user.image,
            },
            create: {
              id: consistentUserId,
              email: user.email,
              name: user.name,
              image: user.image,
            },
          });
          
          console.log(`✅ User synced to database: ${user.email} with ID: ${dbUser.id}`);
          
          // Also update any existing documents that might have the old user ID
          // This is a one-time migration for existing users
          if (user.id !== consistentUserId) {
            const updatedDocs = await prisma.document.updateMany({
              where: { userId: user.id },
              data: { userId: consistentUserId }
            });
            
            if (updatedDocs.count > 0) {
              console.log(`🔄 Migrated ${updatedDocs.count} documents to new user ID format`);
            }
          }
          
        } catch (error) {
          console.error("❌ Failed to sync user to database:", error);
        }
      }
    },
  },
  debug: process.env.NODE_ENV === "development",
})

// Helper function to get consistent user ID from email
export function getConsistentUserId(email: string): string {
  return `google_${email.replace(/[^a-zA-Z0-9]/g, '_')}`;
}