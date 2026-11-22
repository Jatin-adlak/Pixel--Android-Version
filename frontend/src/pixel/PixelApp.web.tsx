import "../global.css";
import { WithSkiaWeb } from "@shopify/react-native-skia/lib/module/web";
import { useSyncExternalStore } from "react";

// Keep the browser-only CanvasKit dependency outside Expo Router's route
// discovery graph. Native resolves PixelApp.tsx and uses native Skia directly.
const loadPixel = () => import("./PixelShell");
const skiaOptions = { locateFile: (file: string) => `/${file}` };
const subscribe = () => () => {};

export default function PixelAppWeb() {
  const mounted = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );

  // CanvasKit needs the browser. Keep SSR and the first hydration render equal.
  if (!mounted) return null;

  return <WithSkiaWeb getComponent={loadPixel} opts={skiaOptions} />;
}
