import { Feather } from "@expo/vector-icons";
import { useState } from "react";
import { Pressable, View } from "react-native";
import LoadingImage from "../pixel/loading/LoadingImage";
import { palette } from "../pixel/data";
import type { Publication } from "./types";

const GAP = 8;
export default function SavedPublicationGrid({
  items,
  dark,
  open,
}: {
  items: Publication[];
  dark: boolean;
  open: (item: Publication) => void;
}) {
  const [width, setWidth] = useState(0);
  const cell = Math.max(1, (width - GAP * 2) / 3);
  return (
    <View
      onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
      style={{ flexDirection: "row", flexWrap: "wrap", gap: GAP }}
    >
      {width > 0 &&
        items.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityLabel={`Open saved ${item.kind}: ${item.title}`}
            onPress={() => open(item)}
            style={{ width: cell, height: cell, paddingLeft: 3, paddingTop: 3 }}
          >
            <View
              style={{
                width: "100%",
                height: "100%",
                backgroundColor: palette.blue,
              }}
            >
              <LoadingImage
                dark={dark}
                source={{
                  uri:
                    item.cover_url ||
                    item.images?.[0]?.cover_url ||
                    item.preview_url,
                }}
                resizeMode="cover"
                style={{
                  width: "100%",
                  height: "100%",
                  borderWidth: 2,
                  borderColor: palette.charcoal,
                  transform: [{ translateX: -3 }, { translateY: -3 }],
                }}
              />
              {(item.kind === "moment" || (item.images?.length || 0) > 1) && (
                <View
                  pointerEvents="none"
                  style={{
                    position: "absolute",
                    top: 5,
                    right: 5,
                    backgroundColor: "#181A1DAA",
                    borderRadius: 12,
                    padding: 4,
                  }}
                >
                  <Feather
                    name={item.kind === "moment" ? "play" : "layers"}
                    size={13}
                    color={palette.ivory}
                  />
                </View>
              )}
            </View>
          </Pressable>
        ))}
    </View>
  );
}
