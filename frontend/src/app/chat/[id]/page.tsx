import { getServerSession } from "next-auth";
import authOptions from "@/lib/auth";
import ChatClient from "./chat.client";

export const dynamic = "force-dynamic";

export default async function ChatPage({ params }: { params: { id: string } }) {
  const session = await getServerSession(authOptions);
  if (!session) return null;
  return <ChatClient docId={params.id} />;
}
