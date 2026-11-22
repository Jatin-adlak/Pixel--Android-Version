// Headers and the global inbox can request Home across overlay/provider bounds.
const listeners = new Set<() => void>();
export function onHomeNavigation(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export function goToHome() {
  for (const listener of [...listeners]) listener();
}
