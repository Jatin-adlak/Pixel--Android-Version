import { createContext, useContext } from "react";

type InboxContext = {
  dark: boolean;
  refraction: boolean;
  count: number;
  open: () => void;
  setDark: (value: boolean) => void;
  setRefraction: (value: boolean) => void;
};

// Keep the context outside the provider's lazy drawer dependency graph.
export const AppInboxContext = createContext<InboxContext | null>(null);

export function useAppInbox() {
  const context = useContext(AppInboxContext);
  if (!context) throw new Error("AppInboxProvider is missing.");
  return context;
}
