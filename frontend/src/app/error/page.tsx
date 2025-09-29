"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import Button from "@/components/ui/Button";

function ErrorInner() {
  const searchParams = useSearchParams();
  const error = searchParams.get("error");

  const getErrorMessage = (error: string | null) => {
    switch (error) {
      case "OAuthAccountNotLinked":
        return {
          title: "Account Already Exists",
          message: "An account with this email already exists. Please sign in with your original method or contact support to link your accounts.",
        };
      case "OAuthCallback":
        return {
          title: "Authentication Error",
          message: "There was an error during authentication. Please try again.",
        };
      default:
        return {
          title: "Authentication Error",
          message: "An unexpected error occurred during sign in.",
        };
    }
  };

  const { title, message } = getErrorMessage(error);

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-6">
      <div className="w-full max-w-md rounded-2xl bg白/5 backdrop-blur border border-white/10 p-8 shadow-2xl text-center">
        <h1 className="text-2xl font-bold mb-4 text-red-400">{title}</h1>
        <p className="text-gray-300 mb-8">{message}</p>
        <div className="space-y-4">
          <Link href="/login" className="block">
            <Button className="w-full">Try Again</Button>
          </Link>
          <Link href="/" className="block">
            <Button variant="secondary" className="w-full">Go Home</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}

export default function AuthErrorPage() {
  return (
    <Suspense fallback={null}>
      <ErrorInner />
    </Suspense>
  );
}