import { Feather } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api } from "../auth/api";
import type { PublicProfile } from "../auth/types";
import { palette } from "./data";
import { useSafeAreaInsets } from "react-native-safe-area-context";

export default function UserSearch({ dark }: { dark: boolean }) {
  const theme = dark ? palette.dark : palette.light;
  const safe = useSafeAreaInsets();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PublicProfile[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [profile, setProfile] = useState<PublicProfile | null>(null);
  const [searching, setSearching] = useState(false);
  useEffect(() => {
    if (query.trim().length < 2) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      setError("");
      void api<{ results: PublicProfile[] }>(
        `/users/?q=${encodeURIComponent(query.trim())}`,
        { signal: controller.signal },
      )
        .then((data) => setResults(data.results))
        .catch((e) => {
          if (!controller.signal.aborted) setError(e.message);
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);
  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Search college members"
        onPress={() => setSearching(true)}
        style={[
          styles.search,
          {
            backgroundColor: theme.surface,
            borderColor: theme.text,
          },
        ]}
      >
        <Feather name="search" color={theme.muted} size={19} />
        <Text style={{ color: theme.muted, fontSize: 13 }}>
          Find people on campus
        </Text>
      </Pressable>
      <Modal
        visible={searching}
        animationType="slide"
        onRequestClose={() => setSearching(false)}
      >
        <View
          style={[
            styles.page,
            {
              backgroundColor: theme.background,
              paddingTop: safe.top + 24,
              paddingBottom: safe.bottom + 24,
            },
          ]}
        >
          <View style={styles.header}>
            <Text style={[styles.title, { color: theme.text }]}>
              Campus people
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => setSearching(false)}
            >
              <Text style={{ color: palette.blue, padding: 12 }}>Done</Text>
            </Pressable>
          </View>
          <TextInput
            accessibilityLabel="Search by name or username"
            placeholder="Search name or username"
            placeholderTextColor={theme.muted}
            value={query}
            onChangeText={(value) => {
              setQuery(value);
              setError("");
              setLoading(value.trim().length >= 2);
              if (value.trim().length < 2) {
                setResults([]);
                setLoading(false);
              }
            }}
            autoCapitalize="none"
            autoFocus
            maxLength={80}
            style={[
              styles.input,
              {
                color: theme.text,
                borderColor: theme.text,
                backgroundColor: theme.surface,
              },
            ]}
          />
          <Text style={[styles.small, { color: theme.muted }]}>
            Visible only to signed-in SAIT members. Enter at least two
            characters.
          </Text>
          {loading && <ActivityIndicator color={palette.blue} />}
          {!!error && (
            <Text style={{ color: "#DA6174", padding: 16 }}>{error}</Text>
          )}
          <ScrollView keyboardShouldPersistTaps="handled">
            {results.map((item) => (
              <Pressable
                key={item.id}
                accessibilityRole="button"
                onPress={() => setProfile(item)}
                style={[styles.result, { borderBottomColor: theme.line }]}
              >
                <View style={styles.avatar}>
                  <Feather name="user" size={21} color={palette.ivory} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.name, { color: theme.text }]}>
                    {item.display_name}
                  </Text>
                  <Text style={[styles.small, { color: theme.muted }]}>
                    @{item.username} · {item.department}
                  </Text>
                </View>
                <Feather name="arrow-up-right" size={19} color={palette.blue} />
              </Pressable>
            ))}
            {!loading && query.length >= 2 && !results.length && !error && (
              <Text
                style={[
                  styles.small,
                  { color: theme.muted, textAlign: "center", marginTop: 30 },
                ]}
              >
                No matching campus profiles yet.
              </Text>
            )}
          </ScrollView>
          {profile && (
            <Modal
              visible
              animationType="slide"
              onRequestClose={() => setProfile(null)}
            >
              <ScrollView
                style={{ flex: 1, backgroundColor: theme.background }}
                contentContainerStyle={{
                  flexGrow: 1,
                  padding: 24,
                  paddingTop: safe.top + 24,
                  paddingBottom: safe.bottom + 24,
                }}
              >
                <View
                  style={[
                    styles.avatar,
                    { width: 76, height: 76, marginTop: 25 },
                  ]}
                >
                  <Feather name="user" size={36} color={palette.ivory} />
                </View>
                <Text
                  style={[styles.title, { color: theme.text, marginTop: 24 }]}
                >
                  {profile.display_name}
                </Text>
                <Text style={[styles.small, { color: palette.blue }]}>
                  @{profile.username} · {profile.role}
                </Text>
                <Text
                  style={[styles.small, { color: theme.muted, marginTop: 16 }]}
                >
                  {profile.department}
                  {profile.year ? ` · ${profile.year}` : ""}
                </Text>
                <Text
                  style={{ color: theme.text, lineHeight: 24, marginTop: 24 }}
                >
                  {profile.bio || "A new perspective on campus."}
                </Text>
              </ScrollView>
            </Modal>
          )}
        </View>
      </Modal>
    </>
  );
}
const styles = StyleSheet.create({
  search: {
    minHeight: 52,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 2,
    borderRadius: 24,
    padding: 12,
  },
  page: { flex: 1, padding: 24, paddingTop: 48 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 24,
  },
  title: { fontSize: 28, fontFamily: "NohemiRegular" },
  input: { borderWidth: 1.5, padding: 15, fontSize: 15 },
  small: { fontSize: 12, lineHeight: 20, marginVertical: 6 },
  result: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingVertical: 18,
    borderBottomWidth: 1,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 40,
    backgroundColor: palette.blue,
    alignItems: "center",
    justifyContent: "center",
  },
  name: { fontSize: 15, fontWeight: "700" },
});
