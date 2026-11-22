import { Feather } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "../auth/api";
import { useAuth } from "../auth/AuthProvider";
import type { CampusUser } from "../auth/types";
import { palette, type Tab } from "./data";

const steps: {
  tab: Tab;
  title: string;
  body: string;
  icon: React.ComponentProps<typeof Feather>["name"];
}[] = [
  {
    tab: "Home",
    title: "The best of your campus.",
    body: "Your feed brings together standout moments and photographs, curated and posted by the social media club. Like, comment and save your favourites.",
    icon: "home",
  },
  {
    tab: "Gallery",
    title: "Every event. Every frame.",
    body: "Browse photographs grouped by college event. Open a folder and use Find yourself to search with your own photo and separate consent. Save matches or download the originals.",
    icon: "image",
  },
  {
    tab: "Moments",
    title: "Campus, in motion.",
    body: "A full-screen home for short video clips. Swipe vertically to move between administrator-published moments.",
    icon: "play-circle",
  },
  {
    tab: "Spotlight",
    title: "What’s next. Who’s here.",
    body: "Find upcoming college events and their details. Search for classmates and faculty by name or username and visit their profiles.",
    icon: "compass",
  },
  {
    tab: "Profile",
    title: "Your corner of PIXEL.",
    body: "Your name, bio and saved moments live here. Tap the pencil to edit your profile. Settings in the header contains appearance, liquid glass and sign out. Your college email stays private.",
    icon: "user",
  },
];

export default function AppTour({
  select,
  dark,
}: {
  select: (tab: Tab) => void;
  dark: boolean;
}) {
  const { user, updateUser } = useAuth();
  const safe = useSafeAreaInsets();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const visible = Boolean(user && !user.tour_completed);
  const theme = dark ? palette.dark : palette.light;
  useEffect(() => {
    if (visible) select(steps[step].tab);
  }, [visible, step, select]);
  if (!visible) return null;
  const finish = async () => {
    setBusy(true);
    setError("");
    try {
      updateUser(
        await api<CampusUser>("/me/tour/", { method: "POST", body: "{}" }),
      );
      setStep(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      transparent
      animationType="fade"
      visible
      onRequestClose={() => void finish()}
    >
      <View
        style={[
          styles.backdrop,
          {
            paddingBottom: Math.max(110, safe.bottom + 100),
            paddingTop: safe.top + 22,
          },
        ]}
      >
        <View
          style={[
            styles.card,
            { backgroundColor: theme.background, borderColor: theme.text },
          ]}
        >
          <ScrollView
            style={{ flexGrow: 0, flexShrink: 1 }}
            showsVerticalScrollIndicator={false}
          >
            <Text style={styles.eyebrow}>
              WELCOME TO PIXEL · {step + 1} / {steps.length}
            </Text>
            <Feather
              name={steps[step].icon}
              color={palette.blue}
              size={30}
              style={{ marginVertical: 18 }}
            />
            <Text style={[styles.title, { color: theme.text }]}>
              {steps[step].title}
            </Text>
            <Text style={[styles.body, { color: theme.muted }]}>
              {steps[step].body}
            </Text>
            {!!error && (
              <Text style={{ color: "#DA6174", marginVertical: 12 }}>
                {error}
              </Text>
            )}
          </ScrollView>
          <View style={styles.row}>
            <Pressable
              disabled={busy}
              accessibilityRole="button"
              onPress={() => void finish()}
            >
              <Text style={{ color: theme.muted, padding: 12 }}>Skip tour</Text>
            </Pressable>
            <Pressable
              disabled={busy}
              accessibilityRole="button"
              onPress={() =>
                step < steps.length - 1 ? setStep(step + 1) : void finish()
              }
              style={styles.next}
            >
              <Text
                style={{
                  color: palette.ivory,
                  fontWeight: "800",
                  fontSize: 13,
                  lineHeight: 19,
                  textAlign: "center",
                }}
              >
                {busy
                  ? "Saving…"
                  : step === steps.length - 1
                    ? "Make yourself at home"
                    : "Next section"}
              </Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}
const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: "flex-end",
    alignItems: "center",
    backgroundColor: "#00000099",
    padding: 22,
    paddingBottom: 110,
  },
  card: {
    width: "100%",
    maxWidth: 430,
    maxHeight: "100%",
    padding: 24,
    borderWidth: 2,
    borderBottomWidth: 5,
    borderBottomColor: palette.blue,
  },
  eyebrow: {
    color: palette.blue,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1,
  },
  title: { fontFamily: "NohemiRegular", fontSize: 26, lineHeight: 33 },
  body: { fontSize: 14, lineHeight: 23, marginTop: 14, marginBottom: 24 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
  },
  next: {
    backgroundColor: palette.blue,
    padding: 13,
    flex: 1,
    minHeight: 46,
    justifyContent: "center",
  },
});
