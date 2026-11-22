import { useEffect, useState } from "react";
import {
  AccessibilityInfo,
  Animated,
  Easing,
  Platform,
  StyleSheet,
  View,
} from "react-native";
import type { DimensionValue, ViewStyle } from "react-native";
import { palette } from "../data";

// One animation value per loader; native opacity/transforms keep layout stationary.
function useLoadingMotion(duration: number) {
  const [value] = useState(() => new Animated.Value(0));
  const [reduced, setReduced] = useState(true);
  useEffect(() => {
    let active = true;
    void AccessibilityInfo.isReduceMotionEnabled().then((enabled) => {
      if (active) setReduced(enabled);
    });
    const subscription = AccessibilityInfo.addEventListener(
      "reduceMotionChanged",
      setReduced,
    );
    return () => {
      active = false;
      subscription.remove();
    };
  }, []);
  useEffect(() => {
    if (reduced) {
      value.setValue(0.5);
      return;
    }
    value.setValue(0);
    const loop = Animated.loop(
      Animated.timing(value, {
        toValue: 1,
        duration,
        easing: Easing.linear,
        useNativeDriver: Platform.OS !== "web",
        isInteraction: false,
      }),
    );
    loop.start();
    return () => loop.stop();
  }, [duration, reduced, value]);
  return value;
}

export function PixelMotionLoader({
  dark = false,
  overlay = false,
  size = 60,
}: {
  dark?: boolean;
  overlay?: boolean;
  size?: number;
}) {
  const motion = useLoadingMotion(1800);
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel="Loading image"
      pointerEvents="none"
      style={[
        overlay ? StyleSheet.absoluteFill : { minHeight: 84 },
        { alignItems: "center", justifyContent: "center" },
      ]}
    >
      <View
        style={{
          width: 60,
          height: 60,
          transform: [{ scale: size / 60 }],
          alignItems: "center",
          justifyContent: "center",
          borderRadius: 18,
          backgroundColor: dark ? "#171B22E8" : "#F7F3E9EB",
        }}
      >
        <View style={{ width: 34, height: 34 }}>
          {Array.from({ length: 9 }, (_, index) => {
            const row = Math.floor(index / 3),
              col = index % 3;
            const peak = 0.2 + (row + col) * 0.13;
            const phase = motion.interpolate({
              inputRange: [0, peak - 0.16, peak, peak + 0.16, 1],
              outputRange: [0, 0, 1, 0, 0],
            });
            return (
              <Animated.View
                key={index}
                style={{
                  position: "absolute",
                  left: col * 12,
                  top: row * 12,
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  backgroundColor:
                    index === 4
                      ? dark
                        ? palette.ivory
                        : palette.charcoal
                      : palette.blue,
                  opacity: phase.interpolate({
                    inputRange: [0, 1],
                    outputRange: [0.25, 1],
                  }),
                  transform: [
                    {
                      scale: phase.interpolate({
                        inputRange: [0, 1],
                        outputRange: [0.65, 1],
                      }),
                    },
                    {
                      translateY: phase.interpolate({
                        inputRange: [0, 1],
                        outputRange: [2, -2],
                      }),
                    },
                  ],
                }}
              />
            );
          })}
        </View>
      </View>
    </View>
  );
}

export function ContentSkeleton({
  dark,
  kind = "list",
}: {
  dark: boolean;
  kind?: "list" | "profile" | "cards" | "post" | "overview";
}) {
  const motion = useLoadingMotion(1800);
  const color = dark ? "#303640" : "#DDD9CF";
  const block = (width: DimensionValue, height: number, extra?: ViewStyle) => (
    <View
      style={{
        width,
        height,
        borderRadius: 7,
        backgroundColor: color,
        ...extra,
      }}
    />
  );
  const row = (key: number) => (
    <View
      key={key}
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: 12,
        paddingVertical: 14,
      }}
    >
      {block(42, 42, { borderRadius: 21 })}
      <View style={{ flex: 1, gap: 9 }}>
        {block("52%", 13)}
        {block("32%", 10)}
      </View>
      {block(56, 26)}
    </View>
  );
  return (
    <Animated.View
      accessibilityRole="progressbar"
      accessibilityLabel={`Loading ${kind === "profile" ? "profile" : "content"}`}
      style={{
        gap: 18,
        width: "100%",
        opacity: motion.interpolate({
          inputRange: [0, 0.5, 1],
          outputRange: [0.5, 0.9, 0.5],
        }),
      }}
    >
      {kind === "profile" && (
        <>
          <View style={{ flexDirection: "row", gap: 16, alignItems: "center" }}>
            {block(64, 64, { borderRadius: 32 })}
            <View style={{ flex: 1, gap: 10 }}>
              {block("55%", 18)}
              {block("35%", 12)}
              {block("70%", 11)}
            </View>
          </View>
          {block("100%", 76, { borderRadius: 28 })}
          <View style={{ flexDirection: "row", gap: 10 }}>
            {[0, 1, 2].map((i) => (
              <View key={i} style={{ flex: 1 }}>
                {block("100%", 34)}
              </View>
            ))}
          </View>
        </>
      )}
      {kind === "list" ? (
        [0, 1, 2, 3].map(row)
      ) : kind === "overview" ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <View
              key={i}
              style={{
                width: "48%",
                height: 126,
                borderRadius: 24,
                backgroundColor: color,
              }}
            />
          ))}
        </View>
      ) : kind === "post" ? (
        <>
          {row(0)}
          <View style={{ aspectRatio: 1, backgroundColor: color }} />
          {block("70%", 12)}
          {block("42%", 10)}
        </>
      ) : (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
          {[0, 1, 2, 3].map((i) => (
            <View key={i} style={{ width: "48%", gap: 10 }}>
              <View style={{ aspectRatio: 0.9, backgroundColor: color }} />
              {block("80%", 12)}
              {block("45%", 10)}
            </View>
          ))}
        </View>
      )}
    </Animated.View>
  );
}
