export type Appearance = { dark: boolean; refraction: boolean };
export async function readAppearance(): Promise<Appearance | null> {
  try {
    const data = JSON.parse(localStorage.getItem("pixel.appearance") || "null");
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
    localStorage.setItem("pixel.appearance", JSON.stringify(value));
  } catch {
    /* Private browsing can block local storage. */
  }
}
