import type { ReactNode } from "react";
import { PixelMotionLoader } from "../pixel/loading/Loading";
import { useAuth } from "./AuthProvider";
import AuthScreen from "./AuthScreen";
import OnboardingScreen from "./OnboardingScreen";
import { Action, AuthPage, Message } from "./ui";

export default function AppGate({ children }: { children: ReactNode }) {
  const { user, loading, config, connectionError, initialize } = useAuth();
  if (loading)
    return (
      <AuthPage
        title={"A moment\nin focus."}
        subtitle="Connecting to your campus…"
      >
        <PixelMotionLoader dark />
      </AuthPage>
    );
  if (!config || connectionError)
    return (
      <AuthPage
        title="Let’s reconnect."
        subtitle="Your campus is a connection away."
      >
        <Message text={connectionError} error />
        <Action onPress={() => void initialize()}>Try again</Action>
      </AuthPage>
    );
  if (!user) return <AuthScreen />;
  if (!user.username || !user.profile_completed) return <OnboardingScreen />;
  return children;
}
