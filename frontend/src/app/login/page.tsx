"use client";

import { useSession } from "next-auth/react";
import { signIn } from "@/lib/auth-client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Button from "@/components/ui/Button";

export default function LoginPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (session) {
      router.push("/dashboard");
    }
  }, [session, router]);

  if (status === "loading") {
    return (
      <div className="flex min-h-[70vh] items-center justify-center px-6">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (session) return null;

  const handleSignIn = async () => {
    await signIn("google", { redirectTo: "/dashboard" });
  };

  return (
    <div className="flex min-h-[70vh] items-center justify-center px-6">
      <div className="w-full max-w-md rounded-2xl bg-white/5 backdrop-blur border border-white/10 p-8 shadow-2xl">
        <h1 className="text-3xl font-bold mb-2">Welcome back</h1>
        <p className="text-gray-400 mb-8">
          Sign in with Google to access your documents and chat history.
        </p>
        <Button
          onClick={handleSignIn}
          className="w-full"
          variant="primary"
        >
          Continue with Google
        </Button>
      </div>
    </div>
  );
}