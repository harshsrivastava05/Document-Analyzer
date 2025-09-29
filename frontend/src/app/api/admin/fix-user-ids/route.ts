// Create frontend/src/app/api/admin/fix-user-ids/route.ts
// CAUTION: Only run this once to fix existing data

import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export async function POST() {
  try {
    const session = await auth();
    if (!session?.user?.email) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    console.log('🔧 MIGRATION: Starting user ID fix for', session.user.email);
    console.log('🔧 MIGRATION: Current session user ID:', session.user.id);

    // Get the expected consistent user ID format
    const consistentUserId = `google_${session.user.email.replace(/[^a-zA-Z0-9]/g, '_')}`;
    console.log('🔧 MIGRATION: Expected consistent user ID:', consistentUserId);

    // Find all documents that might belong to this user but have a different user ID
    const potentialDocuments = await prisma.document.findMany({
      where: {
        userId: {
          not: consistentUserId
        }
      },
      take: 10, // Limit for safety
      orderBy: {
        createdAt: 'desc'
      }
    });

    console.log('🔧 MIGRATION: Found', potentialDocuments.length, 'documents with different user IDs');

    // Also check if there's a user record that needs updating
    const existingUser = await prisma.user.findUnique({
      where: { email: session.user.email }
    });

    let userUpdateResult = null;
    let documentUpdateResult = null;

    if (existingUser && existingUser.id !== consistentUserId) {
      console.log('🔧 MIGRATION: User record needs ID update from', existingUser.id, 'to', consistentUserId);
      
      // Update documents first (before we change the user ID)
      documentUpdateResult = await prisma.document.updateMany({
        where: { userId: existingUser.id },
        data: { userId: consistentUserId }
      });

      // Update chat history
      await prisma.qnA.updateMany({
        where: { userId: existingUser.id },
        data: { userId: consistentUserId }
      });

      // Delete the old user record and create a new one with correct ID
      await prisma.user.delete({
        where: { id: existingUser.id }
      });

      userUpdateResult = await prisma.user.create({
        data: {
          id: consistentUserId,
          email: session.user.email,
          name: session.user.name,
          image: session.user.image,
          emailVerified: existingUser.emailVerified,
        }
      });

      console.log('✅ MIGRATION: User record updated successfully');
    }

    return NextResponse.json({
      message: "Migration completed",
      currentUserId: session.user.id,
      expectedUserId: consistentUserId,
      userNeedsUpdate: existingUser?.id !== consistentUserId,
      userUpdateResult: userUpdateResult ? "Updated" : "No update needed",
      documentsUpdated: documentUpdateResult?.count || 0,
      potentialDocuments: potentialDocuments.map(doc => ({
        id: doc.id,
        title: doc.title,
        userId: doc.userId,
        createdAt: doc.createdAt
      }))
    });

  } catch (error) {
    console.error('🔧 MIGRATION ERROR:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Migration failed" },
      { status: 500 }
    );
  }
}