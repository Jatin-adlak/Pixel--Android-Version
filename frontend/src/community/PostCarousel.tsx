import { Feather } from "@expo/vector-icons";
import { useEffect, useRef, useState, type ComponentRef } from "react";
import { Image, Pressable, ScrollView, Text, View } from "react-native";
import LoadingImage from "../pixel/loading/LoadingImage";
import { palette } from "../pixel/data";
import type { Publication } from "./types";
import { postFrame, type PhotoSize } from "./postFrame";

export default function PostCarousel({
  item,
  dark,
  open,
}: {
  item: Publication;
  dark: boolean;
  open: (index: number) => void;
}) {
  const images = item.images?.length
    ? item.images
    : [
        {
          id: "legacy",
          cover_url: item.cover_url,
          preview_url: item.preview_url,
          width: item.image_width,
          height: item.image_height,
        },
      ];
  const [width, setWidth] = useState(0);
  const [index, setIndex] = useState(0);
  const [measured, setMeasured] = useState<Record<string, PhotoSize>>({});
  const dimensions = images.map((image) =>
    image.width && image.height
      ? { width: image.width, height: image.height }
      : measured[image.preview_url || image.cover_url],
  );
  const frame = postFrame(width, dimensions);
  const sources = images
    .map((image) =>
      image.width && image.height ? "" : image.preview_url || image.cover_url,
    )
    .filter(Boolean)
    .join("\n");
  useEffect(() => {
    let current = true;
    for (const uri of sources.split("\n").filter(Boolean)) {
      Image.getSize(
        uri,
        (width, height) => {
          if (current && width && height)
            setMeasured((old) => ({ ...old, [uri]: { width, height } }));
        },
        () => {},
      );
    }
    return () => {
      current = false;
    };
  }, [sources]);
  const scroll = useRef<ComponentRef<typeof ScrollView>>(null);
  const move = (next: number) => {
    setIndex(next);
    scroll.current?.scrollTo({ x: next * width, animated: true });
  };
  return (
    <View
      style={{
        marginLeft: 4,
        marginTop: 5,
        marginBottom: 8,
        backgroundColor: palette.blue,
      }}
    >
      <View
        style={{
          transform: [{ translateX: -4 }, { translateY: -5 }],
          borderWidth: 3,
          borderColor: palette.charcoal,
          backgroundColor: dark ? "#000" : "#FFF",
        }}
      >
        <ScrollView
          onLayout={(e) => {
            const next = e.nativeEvent.layout.width;
            setWidth(next);
            scroll.current?.scrollTo({ x: index * next, animated: false });
          }}
          ref={scroll}
          horizontal
          pagingEnabled
          directionalLockEnabled
          nestedScrollEnabled
          showsHorizontalScrollIndicator={false}
          onMomentumScrollEnd={(e) => {
            if (width)
              setIndex(
                Math.max(
                  0,
                  Math.min(
                    images.length - 1,
                    Math.round(e.nativeEvent.contentOffset.x / width),
                  ),
                ),
              );
          }}
          style={{ height: frame.height }}
        >
          {!!width &&
            images.map((image, i) => (
              <Pressable
                key={image.id}
                accessibilityRole="button"
                accessibilityLabel={`Open photo ${i + 1} of ${images.length}`}
                onPress={() => open(i)}
                style={{
                  width,
                  height: frame.height,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <LoadingImage
                  dark={dark}
                  source={{ uri: image.preview_url || image.cover_url }}
                  style={{
                    width: dimensions[i]
                      ? dimensions[i]!.width * frame.scale
                      : width,
                    height: dimensions[i]
                      ? dimensions[i]!.height * frame.scale
                      : frame.height,
                    backgroundColor: dark ? "#000" : "#FFF",
                  }}
                  resizeMode="contain"
                />
              </Pressable>
            ))}
        </ScrollView>
        {images.length > 1 && (
          <>
            <View
              pointerEvents="none"
              style={{
                position: "absolute",
                top: 10,
                right: 10,
                backgroundColor: "#181A1DBB",
                borderRadius: 16,
                paddingHorizontal: 10,
                paddingVertical: 5,
              }}
            >
              <Text style={{ color: palette.ivory, fontSize: 11 }}>
                {index + 1} / {images.length}
              </Text>
            </View>
            {(
              [
                [-1, "chevron-left"],
                [1, "chevron-right"],
              ] as const
            ).map(([step, icon]) => (
              <Pressable
                key={icon}
                accessibilityRole="button"
                accessibilityLabel={step < 0 ? "Previous photo" : "Next photo"}
                disabled={index + step < 0 || index + step >= images.length}
                onPress={() => move(index + step)}
                style={{
                  position: "absolute",
                  top: "45%",
                  ...(step < 0 ? { left: 6 } : { right: 6 }),
                  height: 44,
                  width: 36,
                  borderRadius: 22,
                  backgroundColor: "#181A1D99",
                  justifyContent: "center",
                  alignItems: "center",
                  opacity:
                    index + step < 0 || index + step >= images.length ? 0 : 1,
                }}
              >
                <Feather name={icon} size={22} color={palette.ivory} />
              </Pressable>
            ))}
          </>
        )}
      </View>
    </View>
  );
}
