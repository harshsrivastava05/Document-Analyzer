// frontend/src/app/providers.tsx
"use client";

import { SessionProvider } from "next-auth/react";
import { ReactNode } from "react";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider
      refetchOnWindowFocus={true}
      refetchInterval={5 * 60}
    >
      {children}
    </SessionProvider>
  );
}