import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import UploadClient from "./upload.client";

export const dynamic = "force-dynamic";

export default async function UploadPage() {
  const session = await auth();
  
  if (!session) {
    redirect("/login");
  }
  
  return <UploadClient />;
}