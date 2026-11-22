import { useState } from "react";
import { ScrollView, Text, View } from "react-native";
import AppModal from "../pixel/AppModal";
import type { AuthConfig, PolicyInput } from "./types";
import { Action, Check, Message, PolicyModal, authStyles as s } from "./ui";

export default function GoogleSignInConsent({
  config,
  close,
  continueWithGoogle,
}: {
  config: AuthConfig;
  close: () => void;
  continueWithGoogle: (policy: PolicyInput) => Promise<void>;
}) {
  const [privacy, setPrivacy] = useState(false);
  const [terms, setTerms] = useState(false);
  const [reading, setReading] = useState<"privacy" | "terms" | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async () => {
    if (!privacy || !terms || busy) return;
    setBusy(true);
    setError("");
    try {
      await continueWithGoogle({
        privacy_accepted: privacy,
        terms_accepted: terms,
        privacy_version: config.privacy_version,
        terms_version: config.terms_version,
      });
      close();
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "Google sign-in could not start. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <AppModal
      visible
      transparent
      animationType="fade"
      onRequestClose={() => {
        if (!busy) close();
      }}
    >
      <View
        pointerEvents="box-none"
        style={{
          flex: 1,
          backgroundColor: "#00000099",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        <ScrollView
          style={{
            width: "100%",
            maxWidth: 420,
            maxHeight: "90%",
            flexGrow: 0,
            borderRadius: 20,
            backgroundColor: "#181A1D",
          }}
          contentContainerStyle={{ padding: 24, gap: 12 }}
        >
          <Text
            style={[s.label, { fontSize: 22, fontFamily: "NohemiRegular" }]}
          >
            Continue with Google
          </Text>
          <Text style={[s.muted, { lineHeight: 21 }]}>
            Use your college Google account. These agreements apply to Google
            sign-in; the email and password fields are not required.
          </Text>
          <Check
            checked={privacy}
            onChange={() => setPrivacy((old) => !old)}
            label="I have read the Privacy Policy for Google sign-in"
          >
            <Text style={s.muted}>
              I have read the{" "}
              <Text
                accessibilityRole="link"
                style={s.link}
                onPress={() => setReading("privacy")}
              >
                Privacy Policy
              </Text>
              .
            </Text>
          </Check>
          <Check
            checked={terms}
            onChange={() => setTerms((old) => !old)}
            label="I agree to the Terms for Google sign-in"
          >
            <Text style={s.muted}>
              I agree to the{" "}
              <Text
                accessibilityRole="link"
                style={s.link}
                onPress={() => setReading("terms")}
              >
                Terms & campus community rules
              </Text>
              .
            </Text>
          </Check>
          <Message text={error} error />
          <Action
            onPress={() => void submit()}
            busy={busy}
            disabled={!privacy || !terms}
          >
            Continue with Google
          </Action>
          <Action secondary onPress={close} disabled={busy}>
            Cancel
          </Action>
        </ScrollView>
      </View>
      {reading && (
        <PolicyModal
          title={reading === "privacy" ? "Privacy Policy" : "Campus terms"}
          text={config[reading]}
          close={() => setReading(null)}
        />
      )}
    </AppModal>
  );
}
