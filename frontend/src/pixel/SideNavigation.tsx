import { Feather } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import {
  Animated,
  PanResponder,
  Pressable,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import AppModal from "./AppModal";
import PageHeader from "./PageHeader";
import { palette, type Tab } from "./data";

const destinations = [
  { title: "Home", icon: "home" },
  { title: "Gallery", icon: "image" },
  { title: "Moments", icon: "play" },
  { title: "Spotlight", icon: "compass" },
  { title: "Profile", icon: "user" },
] as const;
export default function SideNavigation({
  dark,
  tab,
  close,
  select,
  settings,
  admin,
}: {
  dark: boolean;
  tab: Tab;
  close: () => void;
  select: (tab: Tab) => void;
  settings: () => void;
  admin?: () => void;
}) {
  const safe = useSafeAreaInsets();
  const width = Math.min(320, useWindowDimensions().width * 0.84);
  const [progress] = useState(() => new Animated.Value(0));
  const theme = dark ? palette.dark : palette.light;
  useEffect(() => {
    Animated.timing(progress, {
      toValue: 1,
      duration: 220,
      useNativeDriver: true,
    }).start();
  }, [progress]);
  const leave = (action = close) =>
    Animated.timing(progress, {
      toValue: 0,
      duration: 160,
      useNativeDriver: true,
    }).start(() => {
      close();
      if (action !== close) action();
    });
  const pan = PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) =>
      g.dx < -20 && Math.abs(g.dx) > Math.abs(g.dy) * 1.5,
    onPanResponderRelease: (_, g) => {
      if (g.dx < -60) leave();
    },
  });
  return (
    <AppModal visible transparent onRequestClose={() => leave()}>
      <View style={{ flex: 1 }}>
        <PageHeader
          dark={dark}
          title="Menu"
          actions={
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Close navigation"
              onPress={() => leave()}
              style={{ padding: 10 }}
            >
              <Feather name="x" size={22} color={theme.text} />
            </Pressable>
          }
        />
        <Pressable
          accessibilityLabel="Close navigation"
          accessibilityRole="button"
          onPress={() => leave()}
          style={{
            position: "absolute",
            top: safe.top + 60,
            bottom: 0,
            left: 0,
            right: 0,
          }}
        >
          <Animated.View
            style={{
              flex: 1,
              backgroundColor: "#000",
              opacity: progress.interpolate({
                inputRange: [0, 1],
                outputRange: [0, 0.48],
              }),
            }}
          />
        </Pressable>
        <Animated.View
          {...pan.panHandlers}
          accessibilityViewIsModal
          style={{
            position: "absolute",
            top: safe.top + 60,
            left: 0,
            bottom: 0,
            width,
            backgroundColor: theme.background,
            paddingTop: 20,
            paddingBottom: safe.bottom + 20,
            paddingHorizontal: 20,
            transform: [
              {
                translateX: progress.interpolate({
                  inputRange: [0, 1],
                  outputRange: [-width, 0],
                }),
              },
            ],
          }}
        >
          {destinations.map((item) => (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ selected: tab === item.title }}
              key={item.title}
              onPress={() => leave(() => select(item.title))}
              style={{
                flexDirection: "row",
                alignItems: "center",
                gap: 14,
                padding: 15,
                marginBottom: 8,
                borderRadius: 16,
                backgroundColor:
                  tab === item.title ? theme.surface : "transparent",
              }}
            >
              <Feather
                name={item.icon}
                size={21}
                color={tab === item.title ? palette.blue : theme.text}
              />
              <Text style={{ color: theme.text, fontSize: 15 }}>
                {item.title}
              </Text>
            </Pressable>
          ))}
          <View style={{ flex: 1 }} />
          {admin && (
            <Pressable
              accessibilityRole="button"
              onPress={() => leave(admin)}
              style={{ flexDirection: "row", gap: 14, padding: 15 }}
            >
              <Feather name="grid" size={20} color={palette.blue} />
              <Text style={{ color: theme.text }}>Admin dashboard</Text>
            </Pressable>
          )}
          <Pressable
            accessibilityRole="button"
            onPress={() => leave(settings)}
            style={{ flexDirection: "row", gap: 14, padding: 15 }}
          >
            <Feather name="settings" size={20} color={theme.muted} />
            <Text style={{ color: theme.text }}>Settings</Text>
          </Pressable>
        </Animated.View>
      </View>
    </AppModal>
  );
}
