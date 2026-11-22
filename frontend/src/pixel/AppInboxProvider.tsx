import { useEffect, useState } from "react";
import { readAppearance, writeAppearance } from "./appearanceStorage";
import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthProvider";
import FollowRequestInbox, {
  useFollowRequests,
} from "../community/FollowRequestInbox";
import NotificationDrawer from "./NotificationDrawerReady";
import { AppInboxContext } from "./AppInboxContext";
export default function AppInboxProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = useAuth();
  return <AccountInbox key={user?.id || "guest"}>{children}</AccountInbox>;
}
function AccountInbox({ children }: { children: ReactNode }) {
  const requests = useFollowRequests();
  const [dark, setDark] = useState(true);
  const [refraction, setRefraction] = useState(true);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    let active = true;
    void readAppearance().then((value) => {
      if (active && value) {
        setDark(value.dark);
        setRefraction(value.refraction);
      }
    });
    return () => {
      active = false;
    };
  }, []);
  const changeDark = (value: boolean) => {
    setDark(value);
    void writeAppearance({ dark: value, refraction });
  };
  const changeRefraction = (value: boolean) => {
    setRefraction(value);
    void writeAppearance({ dark, refraction: value });
  };
  return (
    <AppInboxContext.Provider
      value={{
        dark,
        refraction,
        setDark: changeDark,
        setRefraction: changeRefraction,
        count: requests.count,
        open: () => {
          void requests.refresh();
          setVisible(true);
        },
      }}
    >
      {children}
      {visible && (
        <NotificationDrawer
          dark={dark}
          refraction={refraction}
          setDark={changeDark}
          setRefraction={changeRefraction}
          items={[]}
          onClose={() => setVisible(false)}
          onOpen={() => setVisible(false)}
          onDelete={() => {}}
          onMarkAllRead={() => {}}
          requestContent={<FollowRequestInbox inbox={requests} dark={dark} />}
          requestCount={requests.count}
        />
      )}
    </AppInboxContext.Provider>
  );
}
