"use client";

import { SessionProvider } from "next-auth/react";
import { ReactNode } from "react";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider
      // Re-fetch session if tab becomes active
      refetchOnWindowFocus={true}
      // Re-fetch session every 5 minutes
      refetchInterval={5 * 60}
    >
      {children}
    </SessionProvider>
  );
}