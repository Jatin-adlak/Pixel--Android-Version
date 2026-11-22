import { useState } from "react";
import { isRunningInExpoGo } from "expo";
import { Pressable, Text, View } from "react-native";
import { api } from "./api";
import { useAuth } from "./AuthProvider";
import GoogleSignInConsent from "./GoogleSignInConsent";
import {
  Action,
  AuthPage,
  authStyles as s,
  Check,
  Field,
  Message,
  PolicyModal,
} from "./ui";

export default function AuthScreen() {
  const { config, login, google } = useAuth();
  const [signup, setSignup] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [privacy, setPrivacy] = useState(false);
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [policyOpen, setPolicyOpen] = useState<"privacy" | "terms" | null>(
    null,
  );
  const [showPassword, setShowPassword] = useState(false);
  const [googleConsent, setGoogleConsent] = useState(false);
  if (!config) return null;
  const policy = {
    privacy_accepted: privacy,
    terms_accepted: terms,
    privacy_version: config.privacy_version,
    terms_version: config.terms_version,
  };
  const run = async (task: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await task();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  };
  const submit = () =>
    run(async () => {
      if (!privacy || !terms)
        throw new Error(
          "Please read and accept both checkboxes before continuing.",
        );
      if (signup) {
        if (!/^[^@\s]+@sait\.ac\.in$/i.test(identifier.trim()))
          throw new Error("Sign up with your @sait.ac.in college email only.");
        if (password !== confirm)
          throw new Error("Your passwords do not match.");
        const result = await api<{ detail: string }>("/auth/register/", {
          method: "POST",
          body: JSON.stringify({ email: identifier, password, ...policy }),
        });
        setPassword("");
        setConfirm("");
        setMessage(result.detail);
      } else await login(identifier.trim(), password, policy);
    });
  const switchMode = () => {
    setSignup(!signup);
    setError("");
    setMessage("");
    setPassword("");
    setConfirm("");
  };

  return (
    <AuthPage
      title={signup ? "Your campus.\nYour people." : "Good to have\nyou back."}
      subtitle={
        signup
          ? "One college. A thousand stories. Join PIXEL with your SAIT email."
          : "Sign in to the moments, people and memories that make SAIT yours."
      }
    >
      <Field
        label={signup ? "College email" : "Username or college email"}
        placeholder={
          signup ? "your.name@sait.ac.in" : "@username or your.name@sait.ac.in"
        }
        value={identifier}
        onChangeText={setIdentifier}
        keyboardType={signup ? "email-address" : "default"}
        autoComplete={signup ? "email" : "username"}
        maxLength={254}
      />
      <Field
        label="Password"
        placeholder={signup ? "At least 12 characters" : "Your password"}
        value={password}
        onChangeText={setPassword}
        secureTextEntry={!showPassword}
        autoComplete={signup ? "new-password" : "current-password"}
        maxLength={128}
      />
      <View
        style={[
          s.row,
          { justifyContent: "space-between", marginTop: -10, marginBottom: 10 },
        ]}
      >
        <Pressable
          onPress={() => setShowPassword(!showPassword)}
          accessibilityRole="button"
        >
          <Text style={s.link}>
            {showPassword ? "Hide password" : "Show password"}
          </Text>
        </Pressable>
        {!signup && (
          <Pressable
            onPress={() =>
              setMessage(
                "Password reset will be added later. Contact pixel.club@sait.ac.in if you need account help.",
              )
            }
            accessibilityRole="button"
          >
            <Text style={s.link}>Forgot password?</Text>
          </Pressable>
        )}
      </View>
      {signup && (
        <>
          <Field
            label="Confirm password"
            placeholder="Enter it once more"
            value={confirm}
            onChangeText={setConfirm}
            secureTextEntry={!showPassword}
            autoComplete="new-password"
            maxLength={128}
          />
          <Text style={[s.muted, { marginBottom: 14 }]}>
            Use 12+ characters. Avoid common passwords, your name and your
            college email.
          </Text>
        </>
      )}
      <Text style={[s.muted, { fontSize: 11, marginTop: 10, marginBottom: 4 }]}>
        FOR EMAIL / PASSWORD SIGN-IN
      </Text>
      <Check
        checked={privacy}
        onChange={() => setPrivacy(!privacy)}
        label="I have read the Privacy Policy"
      >
        <Text style={s.muted}>
          I have read the{" "}
          <Text
            onPress={() => setPolicyOpen("privacy")}
            accessibilityRole="link"
            style={s.link}
          >
            Privacy Policy
          </Text>
          .
        </Text>
      </Check>
      <Check
        checked={terms}
        onChange={() => setTerms(!terms)}
        label="I agree to the Terms and campus community rules"
      >
        <Text style={s.muted}>
          I agree to the{" "}
          <Text
            onPress={() => setPolicyOpen("terms")}
            accessibilityRole="link"
            style={s.link}
          >
            Terms & campus community rules
          </Text>
          .
        </Text>
      </Check>
      <Message text={error} error />
      <Message text={message} />
      <Action
        onPress={() => void submit()}
        busy={busy}
        disabled={!privacy || !terms || !identifier.trim() || !password}
      >
        {signup ? "Create your account" : "Sign in to PIXEL"}
      </Action>
      <Text
        style={[
          s.muted,
          { textAlign: "center", marginTop: 24, marginBottom: 6 },
        ]}
      >
        OR CONTINUE WITH YOUR COLLEGE ACCOUNT
      </Text>
      <Action
        secondary
        onPress={() => {
          setError("");
          if (!config.google_enabled) {
            setError(
              "Google sign-in is awaiting the college OAuth configuration. Email sign-in is available.",
            );
            return;
          }
          setGoogleConsent(true);
        }}
        disabled={busy}
      >
        Continue with Google
      </Action>
      {!config.google_enabled && (
        <Text style={[s.muted, { marginTop: 10, textAlign: "center" }]}>
          Google sign-in setup is pending.
        </Text>
      )}
      {config.google_enabled && isRunningInExpoGo() && (
        <Text style={[s.muted, { marginTop: 10, textAlign: "center" }]}>
          Google sign-in needs the PIXEL app build. Use email/password while
          testing in Expo Go.
        </Text>
      )}
      <View style={[s.row, { justifyContent: "center", marginTop: 22 }]}>
        <Text style={s.muted}>
          {signup ? "Already part of PIXEL?" : "New around here?"}
        </Text>
        <Pressable accessibilityRole="button" onPress={switchMode}>
          <Text style={s.link}>{signup ? "Sign in" : "Create an account"}</Text>
        </Pressable>
      </View>
      {message.includes("verification") && (
        <Pressable
          accessibilityRole="button"
          onPress={() =>
            void run(async () => {
              const result = await api<{ detail: string }>(
                "/auth/resend-verification/",
                { method: "POST", body: JSON.stringify({ email: identifier }) },
              );
              setMessage(result.detail);
            })
          }
        >
          <Text style={[s.link, { textAlign: "center" }]}>
            Resend verification email
          </Text>
        </Pressable>
      )}
      <Text style={[s.muted, { textAlign: "center", marginTop: 18 }]}>
        SAIT MEMBERS ONLY · MANAGED BY THE SOCIAL MEDIA CLUB
      </Text>
      {policyOpen && (
        <PolicyModal
          title={policyOpen === "privacy" ? "Privacy Policy" : "Campus terms"}
          text={config[policyOpen]}
          close={() => setPolicyOpen(null)}
        />
      )}
      {googleConsent && (
        <GoogleSignInConsent
          config={config}
          close={() => setGoogleConsent(false)}
          continueWithGoogle={google}
        />
      )}
    </AuthPage>
  );
}
