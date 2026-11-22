import LoadingImage from "../pixel/loading/LoadingImage";
import { Feather } from "@expo/vector-icons";
import type { ReactNode } from "react";
import { Pressable, Text, View } from "react-native";
import { palette } from "../pixel/data";
import type { Person } from "./types";

export default function MemberRow({
  person,
  dark,
  onPress,
  actions,
}: {
  person: Person;
  dark: boolean;
  onPress?: () => void;
  actions?: ReactNode;
}) {
  const theme = dark ? palette.dark : palette.light;
  const identity = (
    <>
      {person.avatar_url ? (
        <LoadingImage
          dark={dark}
          source={{ uri: person.avatar_url }}
          style={{ width: 36, height: 36, borderRadius: 18 }}
        />
      ) : (
        <View
          style={{
            width: 36,
            height: 36,
            borderRadius: 18,
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: palette.blue,
          }}
        >
          <Feather name="user" size={19} color={palette.ivory} />
        </View>
      )}
      <View style={{ flex: 1, minWidth: 0, gap: 4 }}>
        <Text
          numberOfLines={1}
          style={{ color: theme.text, fontSize: 14, fontWeight: "600" }}
        >
          {person.display_name || person.username}
        </Text>
        <Text numberOfLines={1} style={{ color: theme.muted, fontSize: 12 }}>
          @{person.username}
        </Text>
      </View>
    </>
  );
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
        minHeight: 58,
        paddingVertical: 8,
      }}
    >
      {onPress ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`View @${person.username}`}
          onPress={onPress}
          style={{
            flex: 1,
            minWidth: 0,
            flexDirection: "row",
            alignItems: "center",
            gap: 10,
          }}
        >
          {identity}
        </Pressable>
      ) : (
        <View
          style={{
            flex: 1,
            minWidth: 0,
            flexDirection: "row",
            alignItems: "center",
            gap: 10,
          }}
        >
          {identity}
        </View>
      )}
      {!!actions && (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          {actions}
        </View>
      )}
    </View>
  );
}
