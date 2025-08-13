// frontend/src/app/layout.tsx
import "./globals.css";
import { Inter } from "next/font/google";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import Providers from "./providers";
import AuthDebug from "@/components/AuthDebug";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "DocAnalyzer AI",
  description: "Modern RAG-powered document analyzer",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} bg-[#0B0B10] text-gray-100`} suppressHydrationWarning>
        <Providers>
          <Navbar />
          <main className="min-h-screen">{children}</main>
          <Footer />
          <AuthDebug />
        </Providers>
      </body>
    </html>
  );
}