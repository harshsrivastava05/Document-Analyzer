"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signIn, signOut } from "next-auth/react";
import Button from "./ui/Button";

export default function Navbar() {
  const { data: session, status } = useSession();
  const pathname = usePathname();

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
                onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
              >
                Login
              </Button>
            )}
          </div>
        ) : (
          <nav className="flex items-center gap-2">
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
              onClick={() => signOut({ callbackUrl: "/" })}
            >
              Sign out
            </Button>
          </nav>
        )}
      </div>
    </header>
  );
}
