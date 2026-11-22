import { Feather } from "@expo/vector-icons";
import { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { api, API_URL } from "../auth/api";
import type { Page } from "../community/types";
import BackNavigation from "../pixel/BackNavigation";
import { ContentSkeleton } from "../pixel/loading/Loading";
import { palette } from "../pixel/data";
import type { CommentGroup, ModerationComment } from "./types";
import { Button, Copy, Panel, useAdminTheme } from "./ui";

export default function CommentModeration({
  dark,
  reloadKey,
  requestDelete,
}: {
  dark: boolean;
  reloadKey: number;
  requestDelete: (comment: ModerationComment, done: () => void) => void;
}) {
  const theme = useAdminTheme();
  const [group, setGroup] = useState<CommentGroup | null>(null);
  const [groups, setGroups] = useState<CommentGroup[]>([]);
  const [comments, setComments] = useState<ModerationComment[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [moreBusy, setMoreBusy] = useState(false);
  const [error, setError] = useState("");
  const [next, setNext] = useState<string | null>(null);
  const [count, setCount] = useState(0);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(
      () => {
        setLoading(true);
        setError("");
        setNext(null);
        const path = group
          ? `/management/comments/?publication=${group.id}&q=${encodeURIComponent(query.trim())}`
          : "/management/comments/groups/";
        void api<Page<CommentGroup | ModerationComment>>(path, {
          signal: controller.signal,
        })
          .then((page) => {
            if (controller.signal.aborted) return;
            if (group) setComments(page.results as ModerationComment[]);
            else setGroups(page.results as CommentGroup[]);
            setCount(page.count ?? page.results.length);
            setNext(page.next);
          })
          .catch((e) => {
            if (!controller.signal.aborted) setError(e.message);
          })
          .finally(() => {
            if (!controller.signal.aborted) setLoading(false);
          });
      },
      query ? 250 : 0,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [group, query, reloadKey, revision]);
  const more = async () => {
    if (!next || moreBusy) return;
    setMoreBusy(true);
    const currentGroup = group;
    try {
      const page = await api<Page<CommentGroup | ModerationComment>>(
        next.replace(`${API_URL}/api/v1`, ""),
      );
      if (currentGroup)
        setComments((old) => [
          ...old,
          ...(page.results as ModerationComment[]),
        ]);
      else setGroups((old) => [...old, ...(page.results as CommentGroup[])]);
      setNext(page.next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load more.");
    } finally {
      setMoreBusy(false);
    }
  };
  return (
    <View style={{ gap: 18 }}>
      {group && (
        <>
          <BackNavigation
            onPress={() => {
              setGroup(null);
              setQuery("");
              setComments([]);
              setNext(null);
            }}
          />
          <View style={{ gap: 7 }}>
            <Text
              style={{ color: theme.text, fontSize: 20, fontWeight: "700" }}
            >
              {group.title}
            </Text>
            <Copy>
              {group.kind === "moment"
                ? "Moment"
                : group.kind === "photo"
                  ? "Gallery photo"
                  : "Post"}{" "}
              · {count} {query.trim() ? "matching comments" : "comments"}
            </Copy>
          </View>
          <View
            style={{
              minHeight: 48,
              flexDirection: "row",
              alignItems: "center",
              gap: 10,
              paddingHorizontal: 14,
              borderRadius: 24,
              backgroundColor: theme.surface,
            }}
          >
            <Feather name="search" size={18} color={theme.muted} />
            <TextInput
              testID="pixel-search-input"
              accessibilityLabel="Search comment content"
              placeholder="Search words in comments"
              placeholderTextColor={theme.muted}
              value={query}
              onChangeText={setQuery}
              autoCapitalize="none"
              style={{
                flex: 1,
                minWidth: 0,
                height: 48,
                color: theme.text,
                fontSize: 14,
                borderWidth: 0,
              }}
            />
            {!!query && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Clear comment search"
                onPress={() => setQuery("")}
                style={{
                  minWidth: 32,
                  minHeight: 44,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Feather name="x" size={18} color={theme.muted} />
              </Pressable>
            )}
          </View>
        </>
      )}
      {!!error && <Text style={{ color: "#DA6174" }}>{error}</Text>}
      {loading && !(group ? comments.length : groups.length) ? (
        <ContentSkeleton dark={dark} />
      ) : group ? (
        <>
          {!loading && !comments.length && (
            <Copy>
              {query.trim()
                ? "No comments contain those words. Try another search."
                : "No comments on this post yet."}
            </Copy>
          )}
          {comments.map((comment) => (
            <Panel key={comment.id}>
              <View
                style={{
                  flexDirection: "row",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: 12,
                }}
              >
                <Text
                  style={{
                    color: theme.text,
                    fontSize: 14,
                    fontWeight: "700",
                    flex: 1,
                  }}
                >
                  @{comment.username}
                </Text>
                <View>
                  <Button
                    compact
                    secondary
                    onPress={() =>
                      requestDelete(comment, () =>
                        setRevision((old) => old + 1),
                      )
                    }
                  >
                    Delete
                  </Button>
                </View>
                <Copy>{new Date(comment.created_at).toLocaleDateString()}</Copy>
              </View>
              {!!comment.parent && (
                <Copy>Reply to comment #{comment.parent}</Copy>
              )}
              <Text style={{ color: theme.text, fontSize: 14, lineHeight: 23 }}>
                {comment.text}
              </Text>
            </Panel>
          ))}
        </>
      ) : (
        <>
          <Copy>
            {count} posts, moments and photos with comments. Choose one to
            review its conversation.
          </Copy>
          {!loading && !groups.length && (
            <Copy>Conversations will appear here when members comment.</Copy>
          )}
          {groups.map((item) => (
            <Pressable
              key={item.id}
              accessibilityRole="button"
              accessibilityLabel={`Review comments on ${item.title}`}
              onPress={() => {
                setGroup(item);
                setComments([]);
                setNext(null);
                setCount(item.comment_count);
              }}
              style={({ pressed }) => ({
                backgroundColor: theme.surface,
                borderRadius: 22,
                borderWidth: 1,
                borderColor: theme.line,
                padding: 18,
                minHeight: 104,
                flexDirection: "row",
                alignItems: "center",
                gap: 14,
                opacity: pressed ? 0.75 : 1,
              })}
            >
              <Feather
                name={item.kind === "moment" ? "play" : "image"}
                size={22}
                color={palette.blue}
              />
              <View style={{ flex: 1, gap: 7 }}>
                <Text
                  numberOfLines={2}
                  style={{ color: theme.text, fontSize: 16, fontWeight: "700" }}
                >
                  {item.title}
                </Text>
                <Copy>
                  {item.comment_count} comments ·{" "}
                  {item.kind === "moment"
                    ? "Moment"
                    : item.kind === "photo"
                      ? "Gallery photo"
                      : "Post"}
                </Copy>
                <Copy>
                  Latest · {new Date(item.latest_comment_at).toLocaleString()}
                </Copy>
              </View>
              <Feather name="chevron-right" color={theme.muted} size={20} />
            </Pressable>
          ))}
        </>
      )}
      {!!next && !loading && (
        <Button secondary busy={moreBusy} onPress={() => void more()}>
          Load more
        </Button>
      )}
    </View>
  );
}
