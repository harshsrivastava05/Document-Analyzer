import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import ChatClient from "./chat.client";

export const dynamic = "force-dynamic";

export default async function ChatPage({ 
  params 
}: { 
  params: Promise<{ id: string }> 
}) {
  const session = await auth();
  
  if (!session) {
    redirect("/login");
  }
  
  const resolvedParams = await params;
  
  return <ChatClient docId={resolvedParams.id} />;
}