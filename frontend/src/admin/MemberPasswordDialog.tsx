import { useRef, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { api } from "../auth/api";
import Modal from "../pixel/AppModal";
import type { AdminMember } from "./types";
import { Button, Copy, Field, Heading, Panel, u } from "./ui";

export default function MemberPasswordDialog({
  member,
  close,
  onSaved,
}: {
  member: AdminMember;
  close: () => void;
  onSaved: (member: AdminMember) => void;
}) {
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const saving = useRef(false);

  const save = async () => {
    if (saving.current) return;
    if (password.length < 12) {
      setError("Use at least 12 characters.");
      return;
    }
    if (password !== confirmation) {
      setError("The passwords do not match.");
      return;
    }
    saving.current = true;
    setBusy(true);
    setError("");
    try {
      const updated = await api<AdminMember>(
        `/management/members/${member.id}/password/`,
        { method: "PUT", body: JSON.stringify({ password }) },
      );
      setPassword("");
      setConfirmation("");
      onSaved(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the password.");
    } finally {
      saving.current = false;
      setBusy(false);
    }
  };

  return (
    <Modal
      visible
      transparent
      animationType="fade"
      onRequestClose={() => {
        if (!saving.current) close();
      }}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        style={{ backgroundColor: "#000000AA" }}
        contentContainerStyle={{
          flexGrow: 1,
          justifyContent: "center",
          padding: 24,
        }}
      >
        <View style={{ width: "100%", maxWidth: 480, alignSelf: "center" }}>
          <Panel>
            <Heading>
              {member.has_password ? "Change password" : "Set password"}
            </Heading>
            <Copy>{member.email}</Copy>
            <Copy>
              Use at least 12 characters. Saving signs this member out on all
              devices.
            </Copy>
            {!member.email_verified && (
              <Copy>
                The member still needs to verify their college email before
                signing in.
              </Copy>
            )}
            <Field
              label="New password"
              value={password}
              onChange={setPassword}
              secure
            />
            <Field
              label="Confirm password"
              value={confirmation}
              onChange={setConfirmation}
              secure
            />
            {!!error && (
              <Text
                accessibilityLiveRegion="polite"
                style={{ color: "#DA6174" }}
              >
                {error}
              </Text>
            )}
            <View style={u.row}>
              <Button secondary busy={busy} onPress={close}>
                Cancel
              </Button>
              <Button busy={busy} onPress={() => void save()}>
                Save password
              </Button>
            </View>
          </Panel>
        </View>
      </ScrollView>
    </Modal>
  );
}
