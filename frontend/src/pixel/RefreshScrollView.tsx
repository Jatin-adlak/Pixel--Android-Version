import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  PanResponder,
  Platform,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";
import type { ScrollViewProps } from "react-native";
import { palette } from "./data";

export default function RefreshScrollView({
  refreshing,
  onRefresh,
  dark,
  enabled = true,
  children,
  ...props
}: ScrollViewProps & {
  refreshing: boolean;
  onRefresh: () => void;
  dark: boolean;
  enabled?: boolean;
}) {
  const top = useRef(0);
  const refresh = useRef(onRefresh);
  const canPull = useRef(enabled && !refreshing);
  const [pull, setPull] = useState(0);
  useEffect(() => {
    refresh.current = onRefresh;
    canPull.current = enabled && !refreshing;
  }, [onRefresh, enabled, refreshing]);
  const responder = useMemo(
    () =>
      // eslint-disable-next-line react-hooks/refs -- PanResponder registers handlers without invoking them during render.
      PanResponder.create({
        onMoveShouldSetPanResponderCapture: (_, gesture) =>
          canPull.current &&
          top.current <= 0 &&
          gesture.dy > 14 &&
          gesture.dy > Math.abs(gesture.dx) * 1.5,
        onPanResponderMove: (_, gesture) =>
          setPull(Math.max(0, Math.min(88, gesture.dy * 0.55))),
        onPanResponderRelease: (_, gesture) => {
          setPull(0);
          if (gesture.dy >= 90 && canPull.current) {
            canPull.current = false;
            refresh.current();
          }
        },
        onPanResponderTerminate: () => setPull(0),
      }),
    [],
  );
  const theme = dark ? palette.dark : palette.light;
  return (
    <View
      style={{ flex: 1 }}
      {...(Platform.OS === "web" ? responder.panHandlers : {})}
    >
      <ScrollView
        {...props}
        scrollEventThrottle={16}
        onScroll={(event) => {
          top.current = Math.max(0, event.nativeEvent.contentOffset.y);
          props.onScroll?.(event);
        }}
        refreshControl={
          Platform.OS !== "web" && enabled ? (
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={palette.blue}
              colors={[palette.blue]}
            />
          ) : undefined
        }
      >
        {Platform.OS === "web" && enabled && (pull > 0 || refreshing) && (
          <View
            style={{
              height: refreshing ? 40 : pull,
              alignItems: "center",
              justifyContent: "center",
              overflow: "hidden",
            }}
          >
            {refreshing ? (
              <ActivityIndicator color={palette.blue} />
            ) : (
              <Text style={{ color: theme.muted, fontSize: 12 }}>
                {pull >= 49 ? "Release to refresh" : "Pull to refresh"}
              </Text>
            )}
          </View>
        )}
        {children}
      </ScrollView>
    </View>
  );
}
