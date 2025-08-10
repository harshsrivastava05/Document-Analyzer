import { getServerSession } from "next-auth";
import authOptions from "@/lib/auth";
import DashboardClient from "./dashboard.client";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  if (!session) return null;
  return <DashboardClient />;
}
