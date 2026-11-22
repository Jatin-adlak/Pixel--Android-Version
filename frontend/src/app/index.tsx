import AppGate from "../auth/AppGate";
import PixelApp from "../pixel/PixelApp";

export default function Index() {
  return (
    <AppGate>
      <PixelApp />
    </AppGate>
  );
}
