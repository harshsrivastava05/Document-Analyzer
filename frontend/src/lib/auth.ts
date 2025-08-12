import NextAuth from "next-auth"
import Google from "next-auth/providers/google"
import { PrismaAdapter } from "@auth/prisma-adapter"
import { prisma } from "./prisma"

export const { auth, handlers, signIn, signOut } = NextAuth({
  adapter: PrismaAdapter(prisma),
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
      allowDangerousEmailAccountLinking: true,
    }),
  ],
  session: {
    strategy: "database", 
    maxAge: 30 * 24 * 60 * 60, 
  },
  pages: {
    signIn: "/login",
    error: "/auth/error", // Correct path
  },
  callbacks: {
    async session({ session, user }) {
      if (user && session.user) {
        session.user.id = user.id;
      }
      return session;
    },
  },
  events: {
    async linkAccount({ user, account }) {
      console.log("Account linked:", { userId: user.id, provider: account.provider });
    },
  },
  debug: process.env.NODE_ENV === "development",
})