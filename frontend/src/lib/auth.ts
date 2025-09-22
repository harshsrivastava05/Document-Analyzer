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
      // Persist the OAuth access_token and user id to the token right after signin
      if (account && user) {
        token.userId = user.id;
        token.email = user.email;
        token.name = user.name;
        token.image = user.image;
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
      return session;
    },
  },
  events: {
    async signIn({ user, account }) {
      if (account?.provider === "google" && user.email) {
        try {
          // Ensure user exists in database
          await prisma.user.upsert({
            where: { email: user.email },
            update: {
              name: user.name,
              image: user.image,
            },
            create: {
              id: user.id || `user_${Date.now()}`, // Fallback ID if none provided
              email: user.email,
              name: user.name,
              image: user.image,
            },
          });
          console.log(`✅ User synced to database: ${user.email}`);
        } catch (error) {
          console.error("❌ Failed to sync user to database:", error);
        }
      }
    },
  },
  debug: process.env.NODE_ENV === "development",
})