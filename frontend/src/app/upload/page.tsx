import { getServerSession } from "next-auth";
import authOptions from "@/lib/auth";
import UploadClient from "./upload.client";

export const dynamic = "force-dynamic";

export default async function UploadPage() {
  const session = await getServerSession(authOptions);
  if (!session) {
    // Route protection also handled by middleware, but double guard
    return null;
  }
  return <UploadClient />;
}
