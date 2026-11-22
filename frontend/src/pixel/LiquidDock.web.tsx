import { Feather } from "@expo/vector-icons";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { RefObject, ComponentRef } from "react";
import { Animated, PanResponder, Pressable, View } from "react-native";
import { useAppInbox } from "./AppInboxContext";
import { useAppNavigation } from "./AppNavigation";
import { palette, tabs } from "./data";

// Feed the actual compositor backdrop through the same rounded-lens displacement
// field as the native shader, including text, icons, images and playing video.
function displacementMap(width: number, height: number) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(width);
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return "";
  const pixels = context.createImageData(canvas.width, height);
  const radius = height / 2;
  for (let y = 0; y < height; y++)
    for (let x = 0; x < canvas.width; x++) {
      const dx = x - width / 2,
        dy = y - height / 2;
      const qx = Math.abs(dx) - (width / 2 - radius),
        qy = Math.abs(dy);
      const cx = Math.max(qx, 0),
        cy = Math.max(qy, 0),
        length = Math.hypot(cx, cy);
      const distance = length + Math.min(Math.max(qx, qy), 0) - radius;
      const nx = length > 0.001 ? (cx / length) * Math.sign(dx) : 0;
      const ny = length > 0.001 ? (cy / length) * Math.sign(dy) : Math.sign(dy);
      const depth = Math.max(0, Math.min(1, 1 - Math.abs(distance) / 15));
      const interior = Math.max(0, 1 - Math.pow(Math.abs(dy / radius), 4));
      const bx = -(nx * (depth * depth * 12 + 0.65) + dx * 0.035 * interior);
      const by = -(
        ny * (depth * depth * 12 + 0.65) +
        (dy * 0.16 + Math.sin((dx / (width / 2)) * Math.PI) * 3) * interior
      );
      const offset = (y * canvas.width + x) * 4;
      pixels.data[offset] = Math.max(0, Math.min(255, 128 + (bx / 40) * 255));
      pixels.data[offset + 1] = Math.max(
        0,
        Math.min(255, 128 + (by / 40) * 255),
      );
      pixels.data[offset + 2] = 128;
      pixels.data[offset + 3] = 255;
    }
  context.putImageData(pixels, 0, 0);
  return canvas.toDataURL();
}

export default function LiquidDock({
  close,
  bottom = 12,
}: {
  close?: () => void;
  bottom?: number;
  surfaceRef?: RefObject<ComponentRef<typeof View> | null>;
}) {
  const { tab, navigate } = useAppNavigation();
  const { dark: appearanceDark, refraction } = useAppInbox();
  const dark = appearanceDark || tab === "Moments";
  const [width, setWidth] = useState(390);
  const [map, setMap] = useState("");
  const [position] = useState(() => new Animated.Value(0));
  const id = `pixel-lens-${useId().replace(/[^a-zA-Z0-9-]/g, "")}`;
  const dockWidth = Math.min(width - 36, 440),
    cell = (dockWidth - 16) / 5;
  const circle = Math.min(50, cell - 8);
  const current = useRef({ cell, circle, close, navigate, position: 0 });
  const start = useRef(0);
  const theme = dark ? palette.dark : palette.light;
  const icons = ["home", "image", "play", "compass", "user"] as const;
  useEffect(() => {
    current.current = { ...current.current, cell, circle, close, navigate };
  }, [cell, circle, close, navigate]);
  useEffect(() => {
    const frame = requestAnimationFrame(() =>
      setMap(displacementMap(dockWidth, 72)),
    );
    return () => cancelAnimationFrame(frame);
  }, [dockWidth]);
  useEffect(() => {
    const next =
      tabs.findIndex((t) => t.name === tab) * cell + (cell - circle) / 2;
    current.current.position = next;
    Animated.spring(position, {
      toValue: next,
      damping: 18,
      stiffness: 190,
      mass: 0.7,
      useNativeDriver: false,
    }).start();
  }, [tab, cell, circle, position]);
  const pan = useMemo(
    () =>
      // eslint-disable-next-line react-hooks/refs -- PanResponder registers callbacks without invoking them during render.
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, g) =>
          Math.abs(g.dx) > 8 && Math.abs(g.dx) > Math.abs(g.dy),
        onPanResponderGrant: () =>
          position.stopAnimation((value) => {
            start.current = value;
          }),
        onPanResponderMove: (_, g) => {
          const at = Math.max(
            0,
            Math.min(
              current.current.cell * 5 - current.current.circle,
              start.current + g.dx,
            ),
          );
          current.current.position = at;
          position.setValue(at);
        },
        onPanResponderRelease: () => {
          const state = current.current;
          const index = Math.max(
            0,
            Math.min(
              4,
              Math.floor((state.position + state.circle / 2) / state.cell),
            ),
          );
          Animated.spring(position, {
            toValue: index * state.cell + (state.cell - state.circle) / 2,
            damping: 18,
            stiffness: 190,
            useNativeDriver: false,
          }).start();
          state.close?.();
          state.navigate(tabs[index].name);
        },
      }),
    [position],
  );
  const filter = refraction && map ? `url(#${id}) saturate(1.15)` : "none";
  return (
    <View
      pointerEvents="box-none"
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      style={{
        position: "absolute",
        bottom,
        left: 0,
        right: 0,
        height: 72,
        zIndex: 20,
      }}
    >
      <svg
        width="0"
        height="0"
        aria-hidden="true"
        style={{ position: "absolute", pointerEvents: "none" }}
      >
        <defs>
          <filter
            id={id}
            x="-20%"
            y="-100%"
            width="140%"
            height="300%"
            colorInterpolationFilters="sRGB"
          >
            <feImage
              href={map || undefined}
              x="0"
              y="0"
              width={dockWidth}
              height="72"
              preserveAspectRatio="none"
              result="lens-map"
            />
            <feDisplacementMap
              in="SourceGraphic"
              in2="lens-map"
              scale="40"
              xChannelSelector="R"
              yChannelSelector="G"
            />
          </filter>
        </defs>
      </svg>
      <View
        testID="pixel-liquid-tabs"
        {...pan.panHandlers}
        accessibilityRole="tablist"
        style={{
          position: "absolute",
          alignSelf: "center",
          width: dockWidth,
          height: 72,
          borderRadius: 36,
        }}
      >
        <View
          pointerEvents="none"
          testID="pixel-liquid-lens"
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: 36,
            borderWidth: 1,
            borderColor: dark ? "#F7F4EB80" : "#181A1D55",
            backgroundColor: refraction
              ? dark
                ? "#181A1D20"
                : "#F7F4EB20"
              : theme.surface,
            ...({
              backdropFilter: filter,
              WebkitBackdropFilter: filter,
              boxShadow:
                "inset 0 1.5px 1px #FFFFFFB0, inset 0 -1px 1px #8199C360, 0 3px 12px #00000018",
            } as object),
          }}
        />
        <Animated.View
          pointerEvents="none"
          style={{
            position: "absolute",
            top: (72 - circle) / 2,
            left: 8,
            width: circle,
            height: circle,
            borderRadius: circle / 2,
            backgroundColor: palette.blue,
            opacity: 0.94,
            transform: [{ translateX: position }],
            ...({ boxShadow: "inset 0 1px 1px #FFFFFF30" } as object),
          }}
        />
        <View
          style={{
            position: "absolute",
            left: 8,
            right: 8,
            height: 72,
            flexDirection: "row",
          }}
        >
          {tabs.map((item, index) => (
            <Pressable
              key={item.name}
              accessibilityRole="tab"
              accessibilityLabel={item.name}
              accessibilityState={{ selected: tab === item.name }}
              onPress={() => {
                close?.();
                navigate(item.name);
              }}
              style={{
                flex: 1,
                height: 72,
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Feather
                name={icons[index]}
                size={23}
                color={tab === item.name ? palette.ivory : theme.text}
              />
            </Pressable>
          ))}
        </View>
      </View>
    </View>
  );
}
