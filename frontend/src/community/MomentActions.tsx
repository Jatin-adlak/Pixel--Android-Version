import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { Pressable, Text, View } from "react-native";
import { palette } from "../pixel/data";
import type { Publication } from "./types";

export default function MomentActions({
  item,
  like,
  comment,
  share,
  save,
  download,
  event,
}: {
  item: Publication;
  like: () => void;
  comment: () => void;
  share: () => void;
  save: () => void;
  download: () => void;
  event: () => void;
}) {
  const action = (
    name: ComponentProps<typeof Ionicons>["name"],
    label: string,
    press: () => void,
    count?: number,
    selected = false,
  ) => (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected }}
      onPress={press}
      style={{
        alignItems: "center",
        justifyContent: "center",
        minWidth: 44,
        minHeight: 44,
        gap: 3,
      }}
    >
      <Ionicons
        name={name}
        size={26}
        color={selected ? palette.blue : palette.ivory}
      />
      {count !== undefined && (
        <Text style={{ color: palette.ivory, fontSize: 12, fontWeight: "600" }}>
          {count}
        </Text>
      )}
    </Pressable>
  );
  return (
    <View style={{ gap: 12 }}>
      {action(
        item.liked ? "heart" : "heart-outline",
        "Like moment",
        like,
        item.like_count,
        item.liked,
      )}
      {action(
        "chatbubble-outline",
        "Moment comments",
        comment,
        item.comment_count,
      )}
      {action("paper-plane-outline", "Share moment", share)}
      {action(
        item.saved ? "bookmark" : "bookmark-outline",
        "Save moment",
        save,
        undefined,
        item.saved,
      )}
      {action("download-outline", "Download moment", download)}
      {action("images-outline", "Event gallery", event)}
    </View>
  );
}
