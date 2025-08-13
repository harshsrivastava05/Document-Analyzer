import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const { auth, handlers, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
      allowDangerousEmailAccountLinking: true,
    }),
  ],
  session: {
    strategy: "jwt", // Changed from "database" to "jwt"
    maxAge: 30 * 24 * 60 * 60, 
  },
  pages: {
    signIn: "/login",
    error: "/error", // Fixed path
  },
  callbacks: {
    async jwt({ token, account, user }) {
      // Persist the OAuth access_token and user id to the token right after signin
      if (account && user) {
        token.userId = user.id;
      }
      return token;
    },
    async session({ session, token }) {
      // Send properties to the client
      if (token.userId) {
        session.user.id = token.userId as string;
      }
      return session;
    },
  },
  events: {
    async signIn({ user, account }) {
      if (account?.provider === "google" && user.email) {
        // Handle user creation/update in your database here
        // You'll need to create an API route for this
        try {
          await fetch(`${process.env.NEXTAUTH_URL}/api/auth/sync-user`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              id: user.id,
              email: user.email,
              name: user.name,
              image: user.image,
            }),
          });
        } catch (error) {
          console.error("Failed to sync user:", error);
        }
      }
    },
  },
  debug: process.env.NODE_ENV === "development",
})