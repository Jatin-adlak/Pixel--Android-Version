import Modal from "./AppModal";
import { Feather } from "@expo/vector-icons";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  PanResponder,
  BackHandler,
  Platform,
  Pressable,
  StatusBar,
  StyleSheet,
  useWindowDimensions,
  View,
} from "react-native";
import ProfileSettings from "./ProfileSettings";
import SideNavigation from "./SideNavigation";
import { ModalBackContext } from "./BackNavigation";

import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useAuth } from "../auth/AuthProvider";
import OnboardingScreen from "../auth/OnboardingScreen";
import { Action, AuthPage, Message } from "../auth/ui";
import ContentScreen from "../community/ContentScreen";
import { useAppInbox } from "./AppInboxContext";
import AdminWorkspace from "../admin/AdminWorkspace";
import AppTour from "./AppTour";
import LiquidPage from "./LiquidPage";
import { useAppNavigation } from "./AppNavigation";
import PageHeader from "./PageHeader";
import { palette } from "./data";

export default function PixelShell() {
  const { width: viewportWidth } = useWindowDimensions();
  const desktopNavigation = Platform.OS === "web" && viewportWidth >= 768;
  const safe = useSafeAreaInsets();
  const { user } = useAuth();
  const [settings, setSettings] = useState(false);
  const [menu, setMenu] = useState(false);
  const backHandlers = useRef<(() => void)[]>([]);
  const registerBack = useCallback((handler: () => void) => {
    backHandlers.current.push(handler);
    return () => {
      backHandlers.current = backHandlers.current.filter(
        (item) => item !== handler,
      );
    };
  }, []);
  useEffect(() => {
    const subscription = BackHandler.addEventListener(
      "hardwareBackPress",
      () => {
        const handler = backHandlers.current.at(-1);
        if (!handler) return false;
        handler();
        return true;
      },
    );
    return () => subscription.remove();
  }, []);
  const edgeSwipe = PanResponder.create({
    onMoveShouldSetPanResponder: (_, g) =>
      g.dx > 18 && Math.abs(g.dx) > Math.abs(g.dy) * 2,
    onPanResponderRelease: (_, g) => {
      if (g.dx > 45) setMenu(true);
    },
  });
  const [admin, setAdmin] = useState(false);
  const { tab, navigate: setTab, version } = useAppNavigation();
  const { dark } = useAppInbox();
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");
  const [size, setSize] = useState({ width: 390, height: 844 });
  const theme = dark ? palette.dark : palette.light;
  const h = size.height;
  const dockY = h - Math.max(safe.bottom, 12) - 86;
  return (
    <ModalBackContext.Provider value={registerBack}>
      <View style={{ flex: 1, backgroundColor: theme.background }}>
        <Pressable
          accessible={false}
          onPress={() => backHandlers.current.at(-1)?.()}
          style={{ position: "absolute", top: 0, bottom: 0, left: 0, right: 0 }}
        />
        <StatusBar barStyle={dark ? "light-content" : "dark-content"} />
        <LiquidPage
          style={s.stage}
          onLayout={(e) => setSize(e.nativeEvent.layout)}
        >
          <View
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              zIndex: 100,
            }}
          >
            <PageHeader
              dark={dark}
              title={tab}
              onMenu={desktopNavigation ? () => setMenu(true) : undefined}
              actions={
                tab === "Profile" ? (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Settings"
                    onPress={() => setSettings(true)}
                    style={s.icon}
                  >
                    <Feather name="settings" size={22} color={theme.text} />
                  </Pressable>
                ) : undefined
              }
            />
          </View>
          <View
            style={{
              position: "absolute",
              top: safe.top + 60,
              left: 0,
              right: 0,
              bottom: 0,
              overflow: "hidden",
            }}
          >
            <ContentScreen
              key={`${tab}-${editing}-${version}`}
              tab={tab}
              dark={dark}
              height={Math.max(220, dockY - safe.top - 145)}
              onEdit={() => setEditing(true)}
              onAdmin={() => setAdmin(true)}
            />
          </View>
        </LiquidPage>
        {desktopNavigation && (
          <View
            {...edgeSwipe.panHandlers}
            style={{
              position: "absolute",
              top: safe.top + 60,
              bottom: 120,
              left: 0,
              width: 16,
            }}
          />
        )}
        {desktopNavigation && menu && (
          <SideNavigation
            dark={dark}
            tab={tab}
            close={() => setMenu(false)}
            select={setTab}
            settings={() => setSettings(true)}
            admin={
              user?.role === "Administrator" ? () => setAdmin(true) : undefined
            }
          />
        )}
        {settings && <ProfileSettings close={() => setSettings(false)} />}
        <AppTour select={setTab} dark={dark} />
        {admin && user?.role === "Administrator" && (
          <AdminWorkspace dark={dark} close={() => setAdmin(false)} />
        )}
        {editing && (
          <Modal
            visible
            animationType="none"
            onRequestClose={() => setEditing(false)}
          >
            <LiquidPage
              closeDock={() => setEditing(false)}
              style={{ backgroundColor: theme.background }}
            >
              <PageHeader dark={dark} title="Edit profile" />
              <OnboardingScreen
                onComplete={() => setEditing(false)}
                onCancel={() => setEditing(false)}
              />
            </LiquidPage>
          </Modal>
        )}
        {!!error && (
          <Modal visible transparent onRequestClose={() => setError("")}>
            <AuthPage title="A small pause." subtitle="Please try again.">
              <Message text={error} error />
              <Action onPress={() => setError("")}>Continue to PIXEL</Action>
            </AuthPage>
          </Modal>
        )}
      </View>
    </ModalBackContext.Provider>
  );
}
const s = StyleSheet.create({
  stage: {
    flex: 1,
    width: "100%",
    maxWidth: 600,
    alignSelf: "center",
    overflow: "hidden",
  },
  icon: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
});
