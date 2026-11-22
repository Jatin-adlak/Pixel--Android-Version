import { Feather } from "@expo/vector-icons";
import { useCallback, useEffect, useRef, useState } from "react";
import { Text, View } from "react-native";
import { ContentSkeleton } from "../pixel/loading/Loading";
import MemberRow from "./MemberRow";
import { api, API_URL } from "../auth/api";
import { useAuth } from "../auth/AuthProvider";
import DesignedButton from "../pixel/DesignedButton";
import { palette } from "../pixel/data";
import type { Page, Person } from "./types";

type FollowRequest = { id: number; user: Person; mandatory: boolean };

export function useFollowRequests() {
  const { user } = useAuth();
  const memberId =
    user?.email_verified && user.profile_completed ? user.id : null;
  const [requests, setRequests] = useState<FollowRequest[]>([]);
  const [count, setCount] = useState(0);
  const [next, setNext] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const operation = useRef(false);
  const pending = useRef<AbortController | null>(null);
  const refresh = useCallback(async () => {
    if (!memberId || operation.current) return;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    try {
      const page = await api<Page<FollowRequest>>(
        "/connections/?kind=requests",
        { signal: controller.signal },
      );
      if (controller.signal.aborted) return;
      setRequests(page.results);
      setCount(page.count ?? page.results.length);
      setNext(page.next);
      setError("");
    } catch (e) {
      if (!controller.signal.aborted)
        setError(
          e instanceof Error ? e.message : "Could not load follow requests.",
        );
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [memberId]);
  useEffect(() => {
    let active = true;
    void Promise.resolve().then(() => {
      if (active) void refresh();
    });
    const timer = setInterval(() => void refresh(), 20000);
    return () => {
      active = false;
      clearInterval(timer);
      pending.current?.abort();
    };
  }, [refresh]);
  const respond = async (id: number, accept: boolean) => {
    if (operation.current) return;
    operation.current = true;
    pending.current?.abort();
    setBusy(true);
    setError("");
    let updated = false;
    try {
      await api(`/connections/${id}/`, { method: accept ? "PUT" : "DELETE" });
      setRequests((old) => old.filter((item) => item.id !== id));
      setCount((old) => Math.max(0, old - 1));
      updated = true;
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not update this request.",
      );
    } finally {
      operation.current = false;
      setBusy(false);
      setLoading(false);
    }
    if (updated) await refresh();
  };
  const more = async () => {
    if (!next || operation.current) return;
    operation.current = true;
    pending.current?.abort();
    setBusy(true);
    try {
      const page = await api<Page<FollowRequest>>(
        next.replace(`${API_URL}/api/v1`, ""),
      );
      setRequests((old) => [...old, ...page.results]);
      setNext(page.next);
      setError("");
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not load more requests.",
      );
    } finally {
      operation.current = false;
      setBusy(false);
      setLoading(false);
    }
  };
  return {
    requests,
    count,
    next,
    error,
    loading,
    busy,
    refresh,
    respond,
    more,
  };
}

export default function FollowRequestInbox({
  inbox,
  dark,
}: {
  inbox: ReturnType<typeof useFollowRequests>;
  dark: boolean;
}) {
  const theme = dark ? palette.dark : palette.light;
  return (
    <View style={{ gap: 16 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 9 }}>
        <Feather name="user-plus" size={18} color={palette.blue} />
        <Text style={{ color: theme.text, fontSize: 15, fontWeight: "700" }}>
          Follow requests{inbox.count ? ` · ${inbox.count}` : ""}
        </Text>
      </View>
      {inbox.loading && !inbox.requests.length && (
        <ContentSkeleton dark={dark} />
      )}
      {!!inbox.error && (
        <Text style={{ color: "#DA6174", fontSize: 13 }}>{inbox.error}</Text>
      )}
      {!inbox.loading && !inbox.error && !inbox.requests.length && (
        <Text style={{ color: theme.muted, fontSize: 13, lineHeight: 20 }}>
          You’re all caught up. New follow requests will appear here.
        </Text>
      )}
      {inbox.requests.map((request) => (
        <View
          key={request.id}
          style={{
            borderBottomWidth: 1,
            borderBottomColor: theme.line,
            paddingVertical: 4,
          }}
        >
          <MemberRow
            person={request.user}
            dark={dark}
            actions={
              <>
                <DesignedButton
                  compact
                  label={`Accept follow request from ${request.user.username}`}
                  selected
                  disabled={inbox.busy}
                  onPress={() => void inbox.respond(request.id, true)}
                >
                  Accept
                </DesignedButton>
                <DesignedButton
                  compact
                  label={`Decline follow request from ${request.user.username}`}
                  disabled={inbox.busy}
                  onPress={() => void inbox.respond(request.id, false)}
                >
                  Decline
                </DesignedButton>
              </>
            }
          />
        </View>
      ))}
      {!!inbox.next && (
        <DesignedButton disabled={inbox.busy} onPress={() => void inbox.more()}>
          More requests
        </DesignedButton>
      )}
    </View>
  );
}
