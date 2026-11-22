import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Modal, Platform, Pressable, type ModalProps } from "react-native";
import { ModalBackContext } from "./BackNavigation";
import { onHomeNavigation } from "./homeNavigation";
import {
  SafeAreaProvider,
  initialWindowMetrics,
} from "react-native-safe-area-context";

// Every overlay uses the same edge-to-edge window as the main screen. Otherwise
// Android can inset a second header below the activity's existing header.
const webModalStack: symbol[] = [];
export default function AppModal(props: ModalProps) {
  const [identity] = useState(() => Symbol("modal"));
  const handlers = useRef<(() => void)[]>([]);
  const registerBack = useCallback((handler: () => void) => {
    handlers.current.push(handler);
    return () => {
      handlers.current = handlers.current.filter((item) => item !== handler);
    };
  }, []);
  const requestClose: NonNullable<ModalProps["onRequestClose"]> = (event) => {
    const handler = handlers.current.at(-1);
    if (handler) handler();
    else props.onRequestClose?.(event);
  };
  const close = useRef(requestClose);
  const closeToHome = useRef(props.onRequestClose);
  useLayoutEffect(() => {
    close.current = requestClose;
    closeToHome.current = props.onRequestClose;
  });
  useEffect(() => {
    if (props.visible === false) return;
    return onHomeNavigation(() => closeToHome.current?.(undefined as never));
  }, [props.visible]);
  useEffect(() => {
    if (Platform.OS !== "web" || props.visible === false) return;
    webModalStack.push(identity);
    const escape = (event: KeyboardEvent) => {
      if (
        event.key !== "Escape" ||
        event.defaultPrevented ||
        webModalStack.at(-1) !== identity
      )
        return;
      event.preventDefault();
      close.current(undefined as never);
    };
    window.addEventListener("keydown", escape);
    return () => {
      const index = webModalStack.indexOf(identity);
      if (index >= 0) webModalStack.splice(index, 1);
      window.removeEventListener("keydown", escape);
    };
  }, [identity, props.visible]);
  return (
    <Modal
      presentationStyle={props.transparent ? "overFullScreen" : "fullScreen"}
      statusBarTranslucent
      navigationBarTranslucent
      hardwareAccelerated
      {...props}
      onRequestClose={requestClose}
    >
      <SafeAreaProvider
        initialMetrics={initialWindowMetrics}
        style={{ flex: 1 }}
      >
        <ModalBackContext.Provider value={registerBack}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Close opened view"
            onPress={() => requestClose(undefined as never)}
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: 0,
              right: 0,
            }}
          />
          {props.children}
        </ModalBackContext.Provider>
      </SafeAreaProvider>
    </Modal>
  );
}
