import { WithSkiaWeb } from "@shopify/react-native-skia/lib/module/web";
import type { DrawerProps } from "./Notifications";

const loadDrawer = () =>
  import("./Notifications").then((module) => ({
    default: module.NotificationDrawer,
  }));
const options = { locateFile: (file: string) => `/${file}` };
export default function NotificationDrawerReady(props: DrawerProps) {
  return (
    <WithSkiaWeb
      getComponent={loadDrawer}
      opts={options}
      componentProps={props}
    />
  );
}
