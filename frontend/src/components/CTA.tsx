import Link from "next/link";
import Button from "./ui/Button";

export default function CTA() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <div className="rounded-3xl border border-violet-500/30 bg-gradient-to-br from-violet-700/30 via-fuchsia-700/20 to-blue-700/20 p-10 text-center">
        <h3 className="text-2xl font-bold">
          Turn documents into conversations
        </h3>
        <p className="mt-2 text-gray-300">
          Upload a PDF, ask anything, and get cited, contextual answers.
        </p>
        <div className="mt-6 flex justify-center gap-4">
          <Link href="/upload">
            <Button>Get Started</Button>
          </Link>
          <Link href="/dashboard">
            <Button variant="secondary">View Dashboard</Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
