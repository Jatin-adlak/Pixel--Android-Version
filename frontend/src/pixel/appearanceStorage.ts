import * as SecureStore from "expo-secure-store";

export type Appearance = { dark: boolean; refraction: boolean };
const options = { keychainService: "com.pixel.preferences.v1" };
export async function readAppearance(): Promise<Appearance | null> {
  try {
    const data = JSON.parse(
      (await SecureStore.getItemAsync("pixel.appearance", options)) || "null",
    );
    return typeof data?.dark === "boolean" &&
      typeof data?.refraction === "boolean"
      ? data
      : null;
  } catch {
    return null;
  }
}
export async function writeAppearance(value: Appearance) {
  try {
    await SecureStore.setItemAsync(
      "pixel.appearance",
      JSON.stringify(value),
      options,
    );
  } catch {
    /* Appearance still works for this session if device storage is unavailable. */
  }
}
