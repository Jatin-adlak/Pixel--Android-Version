import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { api } from "../../auth/api";
import { Action, AuthPage, Field, Message } from "../../auth/ui";

export default function VerifyEmail() {
  const { token } = useLocalSearchParams<{ token?: string }>();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      if (password !== confirm) throw new Error("Your passwords do not match.");
      await api("/auth/verify/", {
        method: "POST",
        body: JSON.stringify({ token, password }),
      });
      setDone(true);
      setPassword("");
      setConfirm("");
      // Remove the one-time token from the address bar/history after consumption.
      if (typeof window !== "undefined")
        window.history.replaceState({}, "", "/auth/verify");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthPage
      title={done ? "You’re\nverified." : "Make it\nofficial."}
      subtitle={
        done
          ? "Your college email is verified. Sign in to choose your username and complete your profile."
          : "Confirm your college email by choosing your account password. Use 12 or more characters."
      }
    >
      {done ? (
        <Action onPress={() => router.replace("/")}>Continue to sign in</Action>
      ) : (
        <>
          <Field
            label="Choose password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="new-password"
            maxLength={128}
          />
          <Field
            label="Confirm password"
            value={confirm}
            onChangeText={setConfirm}
            secureTextEntry
            autoComplete="new-password"
            maxLength={128}
          />
          <Message text={error} error />
          <Action
            busy={busy}
            disabled={!token || !password || !confirm}
            onPress={() => void submit()}
          >
            Verify college email
          </Action>
        </>
      )}
    </AuthPage>
  );
}
