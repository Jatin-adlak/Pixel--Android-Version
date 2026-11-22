import { router, usePathname } from "expo-router";
import { createContext, useContext, useEffect, useState } from "react";
import { onHomeNavigation } from "./homeNavigation";
import type { ReactNode } from "react";
import type { Tab } from "./data";

type Navigation = { tab: Tab; version: number; navigate: (tab: Tab) => void };
const Context = createContext<Navigation | null>(null);
export function useAppNavigation() {
  const value = useContext(Context);
  if (!value) throw new Error("AppNavigationProvider is missing.");
  return value;
}
export default function AppNavigationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [tab, setTab] = useState<Tab>("Home");
  const [version, setVersion] = useState(0);
  const path = usePathname();
  useEffect(
    () =>
      onHomeNavigation(() => {
        setTab("Home");
        setVersion((old) => old + 1);
        if (path !== "/") router.replace("/");
      }),
    [path],
  );
  return (
    <Context.Provider
      value={{
        tab,
        version,
        navigate: (next) => {
          setTab(next);
          setVersion((old) => old + 1);
          if (path !== "/") router.replace("/");
        },
      }}
    >
      {children}
    </Context.Provider>
  );
}
