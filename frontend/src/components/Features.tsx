export default function Features() {
  const features = [
    {
      title: "Google Drive Storage",
      desc: "Securely store and retrieve PDFs via Drive API.",
    },
    {
      title: "Gemini + RAG",
      desc: "Cohere embeddings, Pinecone retrieval, Gemini reasoning.",
    },
    {
      title: "Persistent History",
      desc: "All PDFs and Q&A saved to MySQL per user.",
    },
    {
      title: "Minimalist UI",
      desc: "Glass panels, dark-first palette, subtle motion.",
    },
    {
      title: "Secure Login",
      desc: "Google OAuth with NextAuth, route-level guards.",
    },
    {
      title: "Scalable",
      desc: "FastAPI microservice and edge-friendly frontend.",
    },
  ];
  return (
    <section className="mx-auto max-w-7xl px-6 py-12">
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-2xl border border-white/10 bg-white/5 p-6"
          >
            <div className="text-lg font-semibold">{f.title}</div>
            <p className="mt-2 text-gray-400">{f.desc}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
