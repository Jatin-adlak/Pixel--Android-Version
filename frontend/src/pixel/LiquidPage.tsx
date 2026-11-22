import { useRef } from "react";
import type { ComponentRef } from "react";
import { View } from "react-native";
import type { ViewProps } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import LiquidDock from "./LiquidDock";

export default function LiquidPage({
  children,
  closeDock,
  contentWidth = 600,
  ...props
}: ViewProps & { closeDock?: () => void; contentWidth?: number }) {
  const scene = useRef<ComponentRef<typeof View>>(null);
  const safe = useSafeAreaInsets();
  return (
    <View
      pointerEvents="box-none"
      {...props}
      style={[{ flex: 1 }, props.style]}
    >
      <View
        ref={scene}
        collapsable={false}
        pointerEvents="box-none"
        style={{
          flex: 1,
          width: "100%",
          maxWidth: contentWidth,
          alignSelf: "center",
          overflow: "hidden",
        }}
      >
        {children}
      </View>
      <LiquidDock
        surfaceRef={scene}
        close={closeDock}
        bottom={Math.max(safe.bottom, 12) + 14}
      />
    </View>
  );
}
