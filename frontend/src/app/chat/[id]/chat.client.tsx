"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import Button from "@/components/ui/Button";

const fetcher = (u: string) => fetch(u).then((r) => r.json());

export default function ChatClient({ docId }: { docId: string }) {
  const { data, mutate } = useSWR(
    `/api/proxy/chat-history?docId=${docId}`,
    fetcher
  );
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  const ask = async () => {
    if (!question.trim()) return;
    setLoading(true);
    const res = await fetch("/api/proxy/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ docId, question }),
    });
    setLoading(false);
    setQuestion("");
    if (res.ok) await mutate();
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [data]);

  const items = data?.messages || [];

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <h2 className="text-2xl font-bold mb-6">Chat</h2>
      <div className="rounded-2xl border border-white/10 bg-white/5 p-4 max-h-[60vh] overflow-auto">
        {items.map((m: any) => (
          <div key={m.id} className="mb-4">
            <div className="text-xs text-gray-400 mb-1">
              {m.role === "user" ? "You" : "DocAnalyzer"}
            </div>
            <div
              className={`rounded-lg px-4 py-3 ${
                m.role === "user" ? "bg-violet-600/60" : "bg-white/10"
              }`}
            >
              {m.content}
            </div>
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="mt-4 flex gap-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this document…"
          className="flex-1 rounded-lg bg-white/5 border border-white/10 px-4 py-3 focus:outline-none focus:border-violet-500"
        />
        <Button onClick={ask} disabled={loading}>
          {loading ? "Thinking…" : "Ask"}
        </Button>
      </div>
    </div>
  );
}





