import { useState } from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import type { ImageProps } from "react-native";
import { PixelMotionLoader } from "./Loading";
import { palette } from "../data";

export default function LoadingImage(props: ImageProps & { dark?: boolean }) {
  // A new source has its own loading lifetime, including while swiping between photos.
  return <ImageFrame key={JSON.stringify(props.source)} {...props} />;
}
function ImageFrame({
  dark = false,
  style,
  onLoad,
  onError,
  ...props
}: ImageProps & { dark?: boolean }) {
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const dimensions = StyleSheet.flatten(style);
  const size = Math.max(
    18,
    Math.min(
      60,
      typeof dimensions?.width === "number" ? dimensions.width - 8 : 60,
      typeof dimensions?.height === "number" ? dimensions.height - 8 : 60,
    ),
  );
  return (
    <View
      style={[
        { backgroundColor: dark ? "#20252D" : "#E7E3D9" },
        style,
        { overflow: "hidden" },
      ]}
    >
      <Image
        {...props}
        style={StyleSheet.absoluteFill}
        onLoad={(event) => {
          setState("ready");
          onLoad?.(event);
        }}
        onError={(event) => {
          setState("error");
          onError?.(event);
        }}
      />
      {state === "loading" && (
        <PixelMotionLoader dark={dark} overlay size={size} />
      )}
      {state === "error" && (
        <View
          style={[
            StyleSheet.absoluteFill,
            { alignItems: "center", justifyContent: "center", padding: 12 },
          ]}
        >
          <Text
            style={{
              color: dark ? palette.ivory : palette.charcoal,
              fontSize: 12,
              textAlign: "center",
            }}
          >
            Image unavailable
          </Text>
        </View>
      )}
    </View>
  );
}
