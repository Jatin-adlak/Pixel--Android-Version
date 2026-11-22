import LoadingImage from "./loading/LoadingImage";
import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Member } from "../community/types";
import { useAuth } from "../auth/AuthProvider";
import { palette } from "./data";

export default function ProfileHeader({
  dark,
  savedCount,
  onEdit,
  onHeight,
  profile,
  own = true,
  onFollowers,
  onFollowing,
}: {
  dark: boolean;
  savedCount: number;
  onEdit: () => void;
  onHeight: (height: number) => void;
  onError: (message: string) => void;
  profile?: Member;
  own?: boolean;
  onFollowers?: () => void;
  onFollowing?: () => void;
}) {
  const { user } = useAuth();
  const identity = profile || user;
  const theme = dark ? palette.dark : palette.light;
  return (
    <View
      onLayout={(event) => onHeight(Math.ceil(event.nativeEvent.layout.height))}
      style={styles.content}
    >
      <View style={styles.identity}>
        <View style={styles.avatar}>
          {profile?.avatar_url ? (
            <LoadingImage
              dark={dark}
              source={{ uri: profile.avatar_url }}
              style={{ width: 44, height: 44, borderRadius: 22 }}
            />
          ) : (
            <Ionicons name="person" size={28} color={palette.ivory} />
          )}
        </View>
        <View style={{ flex: 1, minWidth: 0 }}>
          <View style={styles.nameRow}>
            <Text style={[styles.name, { color: theme.text, flexShrink: 1 }]}>
              {identity?.display_name || "Pixel member"}
            </Text>
            {own && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Edit profile"
                onPress={onEdit}
                hitSlop={4}
                style={styles.pencil}
              >
                <Ionicons
                  name="pencil-outline"
                  size={17}
                  color={palette.blue}
                />
              </Pressable>
            )}
          </View>
          <Text style={[styles.meta, { color: theme.muted }]}>
            @{identity?.username} · {identity?.role}
          </Text>
          {!!identity?.department && (
            <Text style={[styles.meta, { color: theme.muted }]}>
              {identity.department}
              {identity.year ? ` · ${identity.year}` : ""}
            </Text>
          )}
        </View>
      </View>
      {!!identity?.bio && (
        <Text style={[styles.bio, { color: theme.muted }]}>{identity.bio}</Text>
      )}
      <View
        style={[
          styles.stats,
          { backgroundColor: theme.surface, borderColor: theme.text },
        ]}
      >
        {[
          [String(savedCount), "Saved"],
          [String(profile?.followers || 0), "Followers"],
          [String(profile?.following || 0), "Following"],
        ].map(([value, label]) => (
          <Pressable
            key={label}
            style={styles.stat}
            accessibilityRole={own && label !== "Saved" ? "button" : undefined}
            accessibilityLabel={
              own && label !== "Saved"
                ? `View ${label.toLowerCase()}`
                : undefined
            }
            disabled={!own || label === "Saved"}
            onPress={label === "Followers" ? onFollowers : onFollowing}
          >
            <Text style={[styles.count, { color: theme.text }]}>{value}</Text>
            <Text style={[styles.statLabel, { color: theme.muted }]}>
              {label}
            </Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { gap: 18 },
  identity: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingHorizontal: 8,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: palette.blue,
    alignItems: "center",
    justifyContent: "center",
  },
  name: { fontSize: 20, fontWeight: "700", lineHeight: 26 },
  meta: { fontSize: 11, lineHeight: 17, marginTop: 4 },
  bio: { fontSize: 13, lineHeight: 20, paddingHorizontal: 8 },
  stats: {
    flexDirection: "row",
    minHeight: 76,
    paddingVertical: 14,
    borderWidth: 2,
    borderRadius: 28,
  },
  stat: { flex: 1, alignItems: "center", justifyContent: "center", gap: 4 },
  count: { fontSize: 20, lineHeight: 26, fontWeight: "700" },
  statLabel: { fontSize: 11, lineHeight: 17 },
  nameRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  pencil: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  actionLabel: {
    color: palette.blue,
    fontSize: 13,
    lineHeight: 20,
    fontWeight: "700",
    textAlign: "center",
  },
  admin: {
    minHeight: 46,
    padding: 12,
    borderWidth: 1,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  savedTitle: {
    fontSize: 13,
    fontWeight: "700",
    lineHeight: 20,
    marginTop: 8,
    paddingHorizontal: 2,
  },
});
