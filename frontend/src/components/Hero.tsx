"use client";

import Button from "./ui/Button";
import Link from "next/link";

export default function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(1000px_600px_at_20%_-10%,rgba(139,92,246,0.25),transparent),radial-gradient(1000px_600px_at_80%_10%,rgba(59,130,246,0.2),transparent)]" />
      <div className="mx-auto max-w-7xl px-6 py-24 text-center">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight">
          <span className="bg-gradient-to-r from-violet-400 via-fuchsia-400 to-blue-400 bg-clip-text text-transparent animate-pulse">
            Analyze. Retrieve. Converse.
          </span>
        </h1>
        <p className="mt-6 text-lg text-gray-300">
          A minimalist, modern RAG platform powered by Gemini LLM, Cohere
          embeddings, and Pinecone—secured with Google login.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <Link href="/dashboard">
            <Button>Open Dashboard</Button>
          </Link>
          <Link href="/upload">
            <Button variant="secondary">Upload a Document</Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
