import { clerkMiddleware } from "@clerk/nextjs/server";

/**
 * Clerk session handling only. Planner route protection runs in the server
 * layout so client-side RSC navigation receives a proper redirect response.
 */
export default clerkMiddleware();

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
