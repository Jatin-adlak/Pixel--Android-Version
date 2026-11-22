import { router } from "expo-router";
import AdminWorkspace from "../admin/AdminWorkspace";
import AppGate from "../auth/AppGate";
import { useAuth } from "../auth/AuthProvider";
import { Action, AuthPage, Message } from "../auth/ui";

function Workspace() {
  const { user } = useAuth();
  if (user?.role !== "Administrator")
    return (
      <AuthPage
        title="The club’s workspace."
        subtitle="This area is for campus administrators."
      >
        <Message text="Sign in with an administrator account to publish and manage PIXEL." />
        <Action onPress={() => router.replace("/")}>Continue to PIXEL</Action>
      </AuthPage>
    );
  return <AdminWorkspace dark close={() => router.replace("/")} />;
}
export default function AdminPage() {
  return (
    <AppGate>
      <Workspace />
    </AppGate>
  );
}
