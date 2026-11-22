import { createContext, useContext, useEffect } from "react";
import { BackHandler } from "react-native";

type RegisterBack = (handler: () => void) => () => void;
export const ModalBackContext = createContext<RegisterBack | null>(null);

// Navigation behaviour without an on-screen button. Native modals dispatch
// system Back through onRequestClose rather than through BackHandler.
export default function BackNavigation({ onPress }: { onPress: () => void }) {
  const register = useContext(ModalBackContext);
  useEffect(() => {
    if (register) return register(onPress);
    const listener = BackHandler.addEventListener("hardwareBackPress", () => {
      onPress();
      return true;
    });
    return () => listener.remove();
  }, [register, onPress]);
  return null;
}
