import * as SecureStore from "expo-secure-store";
import { isRunningInExpoGo } from "expo";
import { Alert } from "react-native";
import { createCredentialStore } from "./credentialStore";

const credentials = createCredentialStore(SecureStore, {
  allowMemoryFallback: __DEV__ && isRunningInExpoGo(),
  onMemoryFallback: () => {
    Alert.alert(
      "Session-only login",
      "Expo Go could not securely remember your login on this device. Login details will stay only in this session, and you’ll need to sign in again after restarting the app.",
    );
  },
});

export const readRefresh = () => credentials.read("pixel.refresh");
export const writeRefresh = (value: string) =>
  credentials.write("pixel.refresh", value);
export const clearRefresh = () => credentials.clear("pixel.refresh");
export const readVerifier = () => credentials.read("pixel.oauth.verifier");
export const writeVerifier = (value: string) =>
  credentials.write("pixel.oauth.verifier", value);
export const clearVerifier = () => credentials.clear("pixel.oauth.verifier");
