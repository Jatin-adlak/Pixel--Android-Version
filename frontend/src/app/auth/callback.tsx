import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { Action, AuthPage, Message } from "../../auth/ui";

export default function GoogleCallback() {
  const params = useLocalSearchParams<{ ticket?: string; error?: string }>();
  const auth = useAuth();
  const started = useRef(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (auth.loading || started.current) return;
    started.current = true;
    if (params.error || !params.ticket) {
      return;
    }
    void auth
      .completeGoogle(params.ticket)
      .then(() => router.replace("/"))
      .catch((e) => setError(e.message));
  }, [auth, params.error, params.ticket]);
  const displayError =
    error ||
    (params.error === "cancelled"
      ? "Google sign-in was cancelled."
      : params.error === "invalid_oauth_request" ||
          (!params.ticket && !params.error)
        ? "This Google sign-in link is incomplete or expired. Return to sign in, accept the policy checkboxes, and choose Continue with Google to start a fresh request."
        : params.error || !params.ticket
          ? "Google sign-in requires your verified @sait.ac.in college account. Please try again."
          : "");
  return (
    <AuthPage
      title={displayError ? "Let’s try\nthat again." : "Back to\nyour campus."}
      subtitle={
        displayError
          ? "Restart Google sign-in from PIXEL."
          : "Completing your secure Google sign-in…"
      }
    >
      <Message text={displayError} error />
      {displayError ? (
        <Action onPress={() => router.replace("/")}>Sign in again</Action>
      ) : null}
    </AuthPage>
  );
}
