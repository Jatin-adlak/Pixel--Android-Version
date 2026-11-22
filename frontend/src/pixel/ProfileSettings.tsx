import { Feather } from "@expo/vector-icons";
import { useState } from "react";
import { Pressable, ScrollView, Switch, Text, View } from "react-native";
import DesignedButton from "./DesignedButton";
import { useAuth } from "../auth/AuthProvider";
import { useAppInbox } from "./AppInboxContext";
import AppModal from "./AppModal";
import BackNavigation from "./BackNavigation";
import PageHeader from "./PageHeader";
import { palette } from "./data";

export default function ProfileSettings({ close }: { close: () => void }) {
  const { dark, refraction, setDark, setRefraction } = useAppInbox();
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const theme = dark ? palette.dark : palette.light;
  const signOut = async () => {
    setBusy(true);
    try {
      await logout();
      close();
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not sign out. Try again.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <AppModal visible onRequestClose={close}>
      <View
        pointerEvents="box-none"
        style={{ flex: 1, backgroundColor: theme.background }}
      >
        <PageHeader dark={dark} title="Settings" />
        <ScrollView
          style={{ width: "100%", maxWidth: 600, alignSelf: "center" }}
          contentContainerStyle={{
            padding: 20,
            gap: 24,
            maxWidth: 600,
            width: "100%",
            alignSelf: "center",
          }}
        >
          <BackNavigation onPress={close} />
          <Text
            style={{
              color: theme.text,
              fontSize: 24,
              fontFamily: "NohemiRegular",
            }}
          >
            Make PIXEL yours.
          </Text>
          <View
            style={{
              backgroundColor: theme.surface,
              borderRadius: 20,
              paddingHorizontal: 18,
            }}
          >
            {(
              [
                {
                  icon: "moon",
                  title: "Dark appearance",
                  note: "Switch between the original light and dark themes",
                  value: dark,
                  change: setDark,
                },
                {
                  icon: "droplet",
                  title: "Liquid glass",
                  note: "Refraction and movement in the navigation dock",
                  value: refraction,
                  change: setRefraction,
                },
              ] as const
            ).map((row) => (
              <View
                key={row.title}
                style={{
                  flexDirection: "row",
                  alignItems: "center",
                  gap: 12,
                  minHeight: 84,
                  paddingVertical: 14,
                }}
              >
                <Feather name={row.icon} size={20} color={palette.blue} />
                <View style={{ flex: 1, gap: 5 }}>
                  <Text
                    style={{
                      color: theme.text,
                      fontSize: 14,
                      fontWeight: "600",
                    }}
                  >
                    {row.title}
                  </Text>
                  <Text
                    style={{ color: theme.muted, fontSize: 12, lineHeight: 18 }}
                  >
                    {row.note}
                  </Text>
                </View>
                <Switch
                  accessibilityLabel={row.title}
                  value={row.value}
                  onValueChange={row.change}
                  trackColor={{ true: palette.blue }}
                />
              </View>
            ))}
          </View>
          <Pressable
            accessibilityRole="button"
            disabled={busy}
            onPress={() => setConfirming(true)}
            style={{
              flexDirection: "row",
              alignItems: "center",
              minHeight: 52,
              gap: 12,
            }}
          >
            <Feather name="log-out" size={20} color="#DA6174" />
            <Text style={{ color: "#DA6174", fontSize: 14 }}>
              {busy ? "Signing out…" : "Sign out"}
            </Text>
          </Pressable>
          {confirming && (
            <View style={{ gap: 12 }}>
              <Text style={{ color: theme.muted, fontSize: 13 }}>
                Sign out of PIXEL on this device?
              </Text>
              <View style={{ flexDirection: "row", gap: 12 }}>
                <DesignedButton
                  compact
                  disabled={busy}
                  onPress={() => void signOut()}
                >
                  Sign out
                </DesignedButton>
                <DesignedButton
                  compact
                  disabled={busy}
                  onPress={() => setConfirming(false)}
                >
                  Cancel
                </DesignedButton>
              </View>
            </View>
          )}
          {!!error && (
            <Text accessibilityLiveRegion="polite" style={{ color: "#DA6174" }}>
              {error}
            </Text>
          )}
        </ScrollView>
      </View>
    </AppModal>
  );
}
