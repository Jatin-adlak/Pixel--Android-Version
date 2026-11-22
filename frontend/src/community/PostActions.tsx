import { Ionicons } from "@expo/vector-icons";
import { Pressable, View } from "react-native";
import type { ComponentProps } from "react";
import { palette } from "../pixel/data";
import type { Publication } from "./types";

export default function PostActions({
  item,
  dark,
  like,
  comment,
  share,
  save,
  event,
  download,
}: {
  item: Publication;
  dark: boolean;
  like: () => void;
  comment: () => void;
  share: () => void;
  save: () => void;
  event: () => void;
  download?: () => void;
}) {
  const theme = dark ? palette.dark : palette.light;
  const icon = (
    name: ComponentProps<typeof Ionicons>["name"],
    label: string,
    onPress: () => void,
    selected = false,
  ) => (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected }}
      onPress={onPress}
      style={{
        width: 44,
        height: 44,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Ionicons
        name={name}
        size={23}
        color={selected ? palette.blue : theme.text}
      />
    </Pressable>
  );
  return (
    <View
      style={{
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        marginTop: 6,
      }}
    >
      <View style={{ flexDirection: "row" }}>
        {icon(
          item.liked ? "heart" : "heart-outline",
          item.liked ? "Unlike" : "Like",
          like,
          item.liked,
        )}
        {icon("chatbubble-outline", "Open comments", comment)}
        {icon("paper-plane-outline", "Share", share)}
        {icon("images-outline", "Open event gallery", event)}
        {download && icon("download-outline", "Download original", download)}
      </View>
      {icon(
        item.saved ? "bookmark" : "bookmark-outline",
        item.saved ? "Unsave" : "Save",
        save,
        item.saved,
      )}
    </View>
  );
}
