import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const Context = createContext<{ muted: boolean; toggle: () => void } | null>(
  null,
);
export function MomentAudioProvider({ children }: { children: ReactNode }) {
  const [muted, setMuted] = useState(true);
  const value = useMemo(
    () => ({ muted, toggle: () => setMuted((old) => !old) }),
    [muted],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useMomentAudio() {
  const value = useContext(Context);
  if (!value) throw new Error("MomentAudioProvider is missing.");
  return value;
}
