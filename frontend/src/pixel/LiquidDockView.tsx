import { Feather } from "@expo/vector-icons";
import { useEffect, useMemo, useRef, useState } from "react";
import type { RefObject, ComponentRef } from "react";
import { makeImageFromView } from "@shopify/react-native-skia";
import type { SkImage } from "@shopify/react-native-skia";
import { PanResponder, Platform, Pressable, View } from "react-native";
import { useSharedValue, withSpring } from "react-native-reanimated";
import { GlassScene, hiddenBox } from "./GlassScene";
import { useAppInbox } from "./AppInboxContext";
import { useAppNavigation } from "./AppNavigation";
import { palette, tabs } from "./data";

export default function LiquidDock({
  close,
  bottom = 12,
  surfaceRef,
}: {
  close?: () => void;
  bottom?: number;
  surfaceRef?: RefObject<ComponentRef<typeof View> | null>;
}) {
  const { tab, navigate } = useAppNavigation();
  const { dark: appearanceDark, refraction } = useAppInbox();
  const dark = appearanceDark || tab === "Moments";
  const [width, setWidth] = useState(390);
  const container = useRef<ComponentRef<typeof View>>(null);
  const [backdrop, setBackdrop] = useState<{
    image: SkImage;
    box: [number, number, number, number];
  } | null>(null);
  useEffect(() => {
    if (Platform.OS === "web" || !surfaceRef || !refraction) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const capture = async () => {
      try {
        if (surfaceRef.current && container.current) {
          const source = surfaceRef.current;
          const dock = container.current;
          const [sourceBox, dockBox] = await Promise.all(
            [source, dock].map(
              (node) =>
                new Promise<number[]>((resolve) =>
                  node.measureInWindow((x, y, w, h) => resolve([x, y, w, h])),
                ),
            ),
          );
          const image = await makeImageFromView(
            surfaceRef as unknown as Parameters<typeof makeImageFromView>[0],
          );
          if (active && image)
            setBackdrop({
              image,
              box: [
                sourceBox[0] - dockBox[0],
                sourceBox[1] - dockBox[1],
                sourceBox[2],
                sourceBox[3],
              ],
            });
        }
      } catch {
        // Keep the last valid rendered scene while a view mounts or resizes.
      } finally {
        if (active) timer = setTimeout(capture, 120);
      }
    };
    void capture();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [surfaceRef, refraction]);
  const dockWidth = Math.min(width - 36, 440);
  const x = (width - dockWidth) / 2;
  const cell = (dockWidth - 16) / 5;
  const circle = Math.min(50, cell - 8);
  const selectedX = useSharedValue(x + 8 + (cell - circle) / 2);
  const scroll = useSharedValue(0);
  const handler = useRef({ x, cell, circle, navigate, close });
  const dragStart = useRef(0);
  const icons = ["home", "image", "play", "compass", "user"] as const;
  useEffect(() => {
    handler.current = { x, cell, circle, navigate, close };
  }, [x, cell, circle, navigate, close]);
  useEffect(() => {
    selectedX.set(
      withSpring(
        x +
          8 +
          tabs.findIndex((t) => t.name === tab) * cell +
          (cell - circle) / 2,
        { damping: 18, stiffness: 190, mass: 0.7 },
      ),
    );
  }, [tab, x, cell, circle, selectedX]);
  const pan = useMemo(
    () =>
      // eslint-disable-next-line react-hooks/refs -- PanResponder registers callbacks; it does not invoke them during render.
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, gesture) =>
          Math.abs(gesture.dx) > 8 &&
          Math.abs(gesture.dx) > Math.abs(gesture.dy),
        onPanResponderGrant: () => {
          dragStart.current = selectedX.value;
        },
        onPanResponderMove: (_, gesture) => {
          const { x: left, cell: step, circle: diameter } = handler.current;
          const at = Math.max(
            left + 8,
            Math.min(
              left + 8 + step * 5 - diameter,
              dragStart.current + gesture.dx,
            ),
          );
          selectedX.set(at);
        },
        onPanResponderRelease: () => {
          const current = handler.current;
          const index = Math.max(
            0,
            Math.min(
              4,
              Math.floor(
                (selectedX.value + current.circle / 2 - current.x - 8) /
                  current.cell,
              ),
            ),
          );
          selectedX.set(
            withSpring(
              current.x +
                8 +
                index * current.cell +
                (current.cell - current.circle) / 2,
              { damping: 18, stiffness: 190 },
            ),
          );
          current.close?.();
          current.navigate(tabs[index].name);
        },
      }),
    [selectedX],
  );
  return (
    <View
      ref={container}
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
      {Platform.OS === "web" && refraction && (
        <View
          pointerEvents="none"
          style={{
            position: "absolute",
            left: x,
            top: 0,
            width: dockWidth,
            height: 72,
            borderRadius: 36,
            overflow: "hidden",
            ...({
              backdropFilter: "blur(16px) saturate(1.5)",
              WebkitBackdropFilter: "blur(16px) saturate(1.5)",
            } as object),
          }}
        />
      )}
      <GlassScene
        liveBackdrop={backdrop}
        width={width}
        height={72}
        slots={[]}
        surfaces={[
          hiddenBox,
          hiddenBox,
          hiddenBox,
          hiddenBox,
          hiddenBox,
          hiddenBox,
          [x, 0, dockWidth, 72],
        ]}
        radii={[0, 0, 0, 0, 0, 0, 36]}
        scroll={scroll}
        selectedX={selectedX}
        selection={[0, (72 - circle) / 2, circle, circle]}
        dark={dark}
        refraction={refraction}
        dock
        transparent
      />
      <View
        {...pan.panHandlers}
        accessibilityRole="tablist"
        style={{
          position: "absolute",
          left: x + 8,
          width: dockWidth - 16,
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
              color={
                tab === item.name
                  ? palette.ivory
                  : (dark ? palette.dark : palette.light).text
              }
            />
          </Pressable>
        ))}
      </View>
    </View>
  );
}
