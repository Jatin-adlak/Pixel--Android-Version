import { Feather } from "@expo/vector-icons";
import { Image, Pressable, Text, View } from "react-native";
import type { ReactNode } from "react";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAppInbox } from "./AppInboxContext";
import { palette } from "./data";
import { goToHome } from "./homeNavigation";

export function InboxButton({ dark }: { dark: boolean }) {
  const inbox = useAppInbox();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Inbox, ${inbox.count} pending follow requests`}
      onPress={inbox.open}
      style={{
        width: 44,
        height: 44,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <Feather
        name="bell"
        size={23}
        color={(dark ? palette.dark : palette.light).text}
      />
      {inbox.count > 0 && (
        <View
          style={{
            position: "absolute",
            top: 6,
            right: 6,
            width: 8,
            height: 8,
            borderRadius: 4,
            backgroundColor: palette.blue,
            borderWidth: 1,
            borderColor: palette.ivory,
          }}
        />
      )}
    </Pressable>
  );
}
export default function PageHeader({
  dark,
  title,
  actions,
  onMenu,
}: {
  dark: boolean;
  title?: string;
  actions?: ReactNode;
  onMenu?: () => void;
}) {
  const safe = useSafeAreaInsets();
  const theme = dark ? palette.dark : palette.light;
  return (
    <View
      style={{
        paddingTop: safe.top,
        backgroundColor: theme.background,
        zIndex: 100,
        flexShrink: 0,
      }}
    >
      <View
        style={{
          height: 60,
          width: "100%",
          maxWidth: 600,
          alignSelf: "center",
          paddingHorizontal: 16,
          flexDirection: "row",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            gap: 8,
            flexShrink: 0,
          }}
        >
          {onMenu && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Open navigation"
              onPress={onMenu}
              style={{
                width: 36,
                height: 44,
                alignItems: "center",
                justifyContent: "center",
                marginLeft: -8,
              }}
            >
              <Feather name="menu" size={21} color={theme.text} />
            </Pressable>
          )}
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Pixel home"
            onPress={goToHome}
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 8,
              minHeight: 44,
            }}
          >
            <Image
              source={require("../../assets/images/pixel-logo.png")}
              resizeMode="contain"
              style={{ width: 28, height: 28 }}
            />
            <Text
              style={{
                color: theme.text,
                fontFamily: "NohemiRegular",
                fontSize: 26,
                lineHeight: 32,
                includeFontPadding: false,
                transform: [{ translateY: 2 }],
                letterSpacing: -0.7,
              }}
            >
              Pixel
            </Text>
          </Pressable>
        </View>
        {!!title && (
          <Text
            numberOfLines={1}
            style={{
              flex: 1,
              minWidth: 0,
              textAlign: "right",
              color: theme.muted,
              fontSize: 13,
              lineHeight: 20,
              includeFontPadding: false,
              fontWeight: "600",
              marginRight: 4,
            }}
          >
            {title}
          </Text>
        )}
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            gap: 0,
            minWidth: 0,
            flexShrink: 0,
          }}
        >
          <InboxButton dark={dark} />
          {actions}
        </View>
      </View>
    </View>
  );
}
