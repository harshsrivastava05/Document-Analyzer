// frontend/src/components/Navbar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { signIn, signOut } from "@/lib/auth-client";
import Button from "./ui/Button";
import { useEffect, useState } from "react";

export default function Navbar() {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Show a loading state until mounted to prevent hydration mismatch
  if (!mounted) {
    return (
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0B0B10]/70 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <Link href="/" className="font-semibold text-white tracking-wide">
            DocAnalyzer
          </Link>
          <div className="text-sm text-gray-400">Loading...</div>
        </div>
      </header>
    );
  }

  if (status === "loading") {
    return (
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0B0B10]/70 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <Link href="/" className="font-semibold text-white tracking-wide">
            DocAnalyzer
          </Link>
          <div className="text-sm text-gray-400">Loading...</div>
        </div>
      </header>
    );
  }

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-[#0B0B10]/70 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Link href="/" className="font-semibold text-white tracking-wide">
          DocAnalyzer
        </Link>
        {!session ? (
          <div>
            {pathname !== "/login" && (
              <Button
                onClick={() => signIn("google", { redirectTo: "/dashboard" })}
              >
                Login
              </Button>
            )}
          </div>
        ) : (
          <nav className="flex items-center gap-2">
            <span className="text-sm text-gray-400 mr-2">
              {session.user?.email}
            </span>
            <Link
              href="/dashboard"
              className="rounded-lg px-3 py-2 text-sm text-gray-200 hover:text-white hover:bg-white/5"
            >
              Dashboard
            </Link>
            <Link
              href="/upload"
              className="rounded-lg px-3 py-2 text-sm text-gray-200 hover:text-white hover:bg-white/5"
            >
              Upload
            </Link>
            <Button
              variant="ghost"
              onClick={() => signOut({ redirect: true, callbackUrl: "/" })}
            >
              Sign out
            </Button>
          </nav>
        )}
      </div>
    </header>
  );
}