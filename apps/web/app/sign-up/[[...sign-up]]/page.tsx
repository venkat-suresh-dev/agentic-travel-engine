import { SignUp } from "@clerk/nextjs";

import { AuthShell } from "@/components/auth/auth-shell";

export default function SignUpPage() {
  return (
    <AuthShell
      eyebrow="Get started"
      title="Create your planner account"
      description="Build premium itineraries, track budgets authoritatively, and refine trips through conversation."
    >
      <SignUp
        routing="path"
        path="/sign-up"
        signInUrl="/sign-in"
        forceRedirectUrl="/planner"
      />
    </AuthShell>
  );
}
