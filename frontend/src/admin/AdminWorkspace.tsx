import Modal from "../pixel/AppModal";
import { Feather } from "@expo/vector-icons";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Image,
  Linking,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api, API_URL } from "../auth/api";
import type { Page } from "../community/types";
import { palette } from "../pixel/data";
import BackNavigation from "../pixel/BackNavigation";
import PageHeader from "../pixel/PageHeader";
import { ContentSkeleton } from "../pixel/loading/Loading";
import LoadingImage from "../pixel/loading/LoadingImage";
import LiquidPage from "../pixel/LiquidPage";
import RefreshScrollView from "../pixel/RefreshScrollView";
import EventEditor from "./EventEditor";
import MemberPasswordDialog from "./MemberPasswordDialog";
import Overview from "./Overview";
import CommentModeration from "./CommentModeration";
import PublicationEditor from "./PublicationEditor";
import { appendMedia, chooseMedia } from "./media";
import type {
  AdminEvent,
  AdminMember,
  AdminPublication,
  MediaAsset,
  ModerationComment,
  Storage,
  Summary,
} from "./types";
import {
  AdminAppearance,
  Button,
  Chip,
  Copy,
  Field,
  Heading,
  Panel,
  u,
} from "./ui";

const sections = [
  "Overview",
  "Posts",
  "Moments",
  "Spotlight",
  "Gallery",
  "Comments",
  "Members",
  "Storage",
] as const;
type Section = (typeof sections)[number];
export default function AdminWorkspace({
  dark,
  close,
}: {
  dark: boolean;
  close: () => void;
}) {
  const safe = useSafeAreaInsets();
  const theme = dark ? palette.dark : palette.light;
  const [section, setSection] = useState<Section>("Overview");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [events, setEvents] = useState<AdminEvent[]>([]);
  const [eventChoices, setEventChoices] = useState<AdminEvent[]>([]);
  const [publications, setPublications] = useState<AdminPublication[]>([]);
  const [members, setMembers] = useState<AdminMember[]>([]);
  const [passwordMember, setPasswordMember] = useState<AdminMember | null>(
    null,
  );
  const [commentRevision, setCommentRevision] = useState(0);
  const [storage, setStorage] = useState<Storage | null>(null);
  const [postFolder, setPostFolder] = useState(""),
    [momentFolder, setMomentFolder] = useState("");
  const [next, setNext] = useState<string | null>(null);
  const [gallery, setGallery] = useState<AdminEvent | null>(null);
  const [gallerySync, setGallerySync] = useState<AdminEvent["sync"]>(null);
  const [uploads, setUploads] = useState<MediaAsset[]>([]);
  const [editor, setEditor] = useState<"event" | "publication" | null>(null);
  const [editingEvent, setEditingEvent] = useState<AdminEvent>();
  const [editingPublication, setEditingPublication] =
    useState<AdminPublication>();
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false),
    [loading, setLoading] = useState(true);
  const lock = useRef(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState(""),
    [error, setError] = useState("");
  const [confirm, setConfirm] = useState<{
    title: string;
    detail: string;
    action: () => Promise<void>;
  } | null>(null);
  const path = useCallback(
    () =>
      section === "Posts" || section === "Moments"
        ? `/management/publications/?kind=${section === "Posts" ? "post" : "moment"}`
        : section === "Gallery" && gallery
          ? `/management/publications/?kind=photo&event_id=${gallery.id}`
          : section === "Members"
            ? `/management/members/?q=${encodeURIComponent(query)}`
            : section === "Comments"
              ? "/management/comments/"
              : `/management/${section === "Spotlight" ? "spotlights" : "events"}/`,
    [section, gallery, query],
  );
  const applyStorage = (value: Storage) => {
    setStorage(value);
    setPostFolder(
      value.folders.find((f) => f.kind === "post")?.folder_id || "",
    );
    setMomentFolder(
      value.folders.find((f) => f.kind === "moment")?.folder_id || "",
    );
  };
  const applyPage = useCallback(
    (
      data: Page<
        AdminEvent | AdminPublication | AdminMember | ModerationComment
      >,
      append: boolean,
    ) => {
      if (
        section === "Posts" ||
        section === "Moments" ||
        (section === "Gallery" && gallery)
      )
        setPublications((old) => [
          ...(append ? old : []),
          ...(data.results as AdminPublication[]),
        ]);
      else if (section === "Members")
        setMembers((old) => [
          ...(append ? old : []),
          ...(data.results as AdminMember[]),
        ]);
      else
        setEvents((old) => [
          ...(append ? old : []),
          ...(data.results as AdminEvent[]),
        ]);
      setNext(data.next);
    },
    [section, gallery],
  );
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (section === "Overview")
        setSummary(await api<Summary>("/management/dashboard/"));
      else if (section === "Comments") setCommentRevision((old) => old + 1);
      else if (section === "Storage")
        applyStorage(await api<Storage>("/management/storage/"));
      else
        applyPage(
          await api<
            Page<
              AdminEvent | AdminPublication | AdminMember | ModerationComment
            >
          >(path()),
          false,
        );
      if (section === "Gallery" && gallery) {
        const detail = await api<AdminEvent>(
          `/management/events/${gallery.id}/`,
        );
        setGallerySync(detail.sync);
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not load the workspace.",
      );
    } finally {
      setLoading(false);
    }
  }, [section, path, applyPage, gallery]);
  useEffect(() => {
    void Promise.resolve().then(load);
  }, [load]);
  const run = async (fn: () => Promise<void>) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };
  const navigate = (value: Section) => {
    if (section === value && !editor && !gallery) return;
    setLoading(true);
    setEvents([]);
    setPublications([]);
    setMembers([]);
    setSection(value);
    setEditor(null);
    setGallery(null);
    setUploads([]);
    setMessage("");
    setError("");
    setNext(null);
  };
  const loadEventChoices = async () => {
    const choices: AdminEvent[] = [];
    let url: string | null = "/management/events/";
    while (url) {
      const p: Page<AdminEvent> = await api<Page<AdminEvent>>(url);
      choices.push(...p.results);
      url = p.next?.replace(`${API_URL}/api/v1`, "") || null;
    }
    setEventChoices(choices);
  };
  const newPublication = () =>
    void run(async () => {
      await loadEventChoices();
      setEditingPublication(undefined);
      setEditor("publication");
    });
  const finish = () => {
    setEditor(null);
    setMessage("Saved. Your changes are ready.");
    void load();
  };
  const editPublication = (item: AdminPublication) =>
    void run(async () => {
      await loadEventChoices();
      setEditingPublication(item);
      setEditor("publication");
    });
  const togglePublication = (item: AdminPublication) =>
    void run(async () => {
      await api(`/management/publications/${item.id}/`, {
        method: "PATCH",
        body: JSON.stringify({ published: !item.published }),
      });
      await load();
      setMessage(
        item.published
          ? "Publication moved to drafts."
          : "Publication is live.",
      );
    });
  const uploadGallery = () =>
    void run(async () => {
      if (!gallery || !uploads.length)
        throw new Error("Choose gallery photographs first.");
      const body = new FormData();
      uploads.forEach((file) => appendMedia(body, "files", file));
      const result = await api<{ uploaded: number; failed: string[] }>(
        `/management/events/${gallery.id}/photos/`,
        { method: "POST", body, timeoutMs: 300000 },
      );
      setUploads([]);
      await load();
      setMessage(
        `${result.uploaded} photographs uploaded${result.failed.length ? `. Could not upload: ${result.failed.join(", ")}` : "."}`,
      );
    });
  const smallTitle = (text: string) => (
    <Text style={[u.label, { color: theme.text }]}>{text}</Text>
  );
  const cover = (url?: string) =>
    url ? (
      <LoadingImage
        dark={dark}
        source={{ uri: url }}
        style={{ width: 44, height: 52, borderRadius: 8 }}
        resizeMode="cover"
      />
    ) : (
      <View
        style={{
          width: 44,
          height: 52,
          borderRadius: 8,
          backgroundColor: palette.blue,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Feather name="image" size={26} color={palette.ivory} />
      </View>
    );
  return (
    <AdminAppearance.Provider value={dark}>
      <Modal visible animationType="none" onRequestClose={close}>
        <LiquidPage
          closeDock={close}
          contentWidth={1120}
          style={{
            flex: 1,
            backgroundColor: theme.background,
            paddingTop: 0,
          }}
        >
          <View
            style={{
              width: "100%",
              maxWidth: 1120,
              alignSelf: "center",
              flex: 1,
            }}
          >
            <PageHeader
              dark={dark}
              title="Admin Studio"
              actions={
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Close Admin Studio"
                  onPress={close}
                  style={{ padding: 10 }}
                >
                  <Feather name="x" size={25} color={theme.text} />
                </Pressable>
              }
            />
            <View>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={{ padding: 18, gap: 8 }}
              >
                {sections.map((item) => (
                  <Chip
                    key={item}
                    selected={section === item}
                    onPress={() => navigate(item)}
                  >
                    {item}
                  </Chip>
                ))}
              </ScrollView>
            </View>
            <RefreshScrollView
              refreshing={refreshing}
              enabled={!busy && (!loading || refreshing)}
              onRefresh={() => {
                setRefreshing(true);
                void load().finally(() => setRefreshing(false));
              }}
              dark={dark}
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={{
                paddingHorizontal: 22,
                paddingBottom: safe.bottom + 120,
                gap: 22,
              }}
            >
              {(editor || gallery) && (
                <BackNavigation
                  onPress={() => {
                    setEditor(null);
                    setGallery(null);
                    setUploads([]);
                  }}
                />
              )}
              {!!error && (
                <View
                  accessibilityRole="alert"
                  style={{
                    padding: 18,
                    borderWidth: 1,
                    borderColor: "#DA6174",
                    borderRadius: 14,
                  }}
                >
                  <Text
                    style={{ color: "#DA6174", fontSize: 14, lineHeight: 22 }}
                  >
                    {error}
                  </Text>
                </View>
              )}
              {!!message && (
                <Panel>
                  <Text style={{ color: palette.blue, fontSize: 14 }}>
                    {message}
                  </Text>
                </Panel>
              )}
              {editor === "event" ? (
                <EventEditor
                  key={editingEvent?.id || "new-event"}
                  initial={editingEvent}
                  spotlight={section === "Spotlight"}
                  run={(fn) => void run(fn)}
                  done={finish}
                  busy={busy}
                />
              ) : editor === "publication" ? (
                <PublicationEditor
                  key={editingPublication?.id || "new-publication"}
                  initial={editingPublication}
                  kind={
                    section === "Moments"
                      ? "moment"
                      : section === "Gallery"
                        ? "photo"
                        : "post"
                  }
                  events={eventChoices}
                  run={(fn) => void run(fn)}
                  done={finish}
                  busy={busy}
                />
              ) : (
                <>
                  <View style={{ gap: 12 }}>
                    <Heading eyebrow="YOUR CAMPUS, IN FOCUS">
                      {gallery
                        ? gallery.title
                        : section === "Overview"
                          ? "Behind every perspective."
                          : section === "Storage"
                            ? "A home for every memory."
                            : section}
                    </Heading>
                    <Copy>
                      {section === "Overview"
                        ? "Create, publish and look after the campus community from one place."
                        : section === "Gallery"
                          ? "Event photographs stay connected to their Drive folder in both directions."
                          : section === "Members"
                            ? "Manage campus roles and access. Member emails stay inside this workspace."
                            : section === "Comments"
                              ? "Keep the conversation welcoming. Removing a comment also removes its replies."
                              : section === "Storage"
                                ? "Original files stay in the Pixel Google account. The app stores their details and social activity."
                                : "Create a draft, check its cover and details, then publish when it is ready."}
                    </Copy>
                  </View>
                  {section === "Overview" && summary && (
                    <Overview summary={summary} open={navigate} />
                  )}
                  {(section === "Spotlight" ||
                    (section === "Gallery" && !gallery)) && (
                    <>
                      <View style={u.row}>
                        <Button
                          onPress={() => {
                            setEditingEvent(undefined);
                            setEditor("event");
                          }}
                        >
                          {section === "Spotlight"
                            ? "+ Create announcement"
                            : "+ Add event folder"}
                        </Button>
                      </View>
                      {events.map((event) => (
                        <Panel key={event.id}>
                          <View style={u.row}>
                            {cover(event.cover_preview_url || event.cover_url)}
                            <View style={{ flex: 1, gap: 6 }}>
                              {smallTitle(event.title)}
                              <Copy>
                                {event.tag} ·{" "}
                                {event.published ? "Published" : "Draft"}
                              </Copy>
                              <Copy>
                                {new Date(event.starts_at).toLocaleString(
                                  "en-IN",
                                  { timeZone: "Asia/Kolkata" },
                                )}{" "}
                                · {event.venue}
                              </Copy>
                            </View>
                            <View
                              style={{
                                flexDirection: "row",
                                alignItems: "center",
                                gap: 8,
                              }}
                            >
                              <Button
                                compact
                                secondary
                                label="Edit event details"
                                onPress={() => {
                                  setEditingEvent(event);
                                  setEditor("event");
                                }}
                              >
                                <Feather name="edit-2" size={14} />
                              </Button>
                              {section === "Gallery" && (
                                <Button
                                  compact
                                  secondary
                                  label="Open event folder"
                                  onPress={() => setGallery(event)}
                                >
                                  <Feather name="folder" size={14} />
                                </Button>
                              )}
                              <Button
                                compact
                                secondary
                                label={
                                  event.published
                                    ? "Unpublish event"
                                    : "Publish event"
                                }
                                onPress={() =>
                                  void run(async () => {
                                    await api(
                                      `/management/${section === "Spotlight" ? "spotlights" : "events"}/${event.id}/`,
                                      {
                                        method: "PATCH",
                                        body: JSON.stringify({
                                          published: !event.published,
                                        }),
                                      },
                                    );
                                    await load();
                                  })
                                }
                              >
                                <Feather
                                  name={event.published ? "eye-off" : "upload"}
                                  size={14}
                                />
                              </Button>
                            </View>
                          </View>
                        </Panel>
                      ))}
                    </>
                  )}
                  {section === "Gallery" && gallery && (
                    <>
                      <Panel>
                        <View style={u.row}>
                          <Button
                            secondary
                            busy={busy}
                            onPress={() =>
                              void run(async () => {
                                const files = await chooseMedia(false, true);
                                setUploads(files);
                              })
                            }
                          >
                            Choose photographs
                          </Button>
                          <Button busy={busy} onPress={uploadGallery}>
                            Upload {uploads.length || ""} photos
                          </Button>
                          <Button
                            secondary
                            busy={busy}
                            onPress={() =>
                              void run(async () => {
                                await api(
                                  `/management/events/${gallery.id}/sync/`,
                                  { method: "POST", timeoutMs: 180000 },
                                );
                                await load();
                                setMessage("Gallery synchronized with Drive.");
                              })
                            }
                          >
                            Sync with Drive
                          </Button>
                        </View>
                        {uploads.length > 0 && (
                          <>
                            <Copy>
                              {uploads.length} selected · originals will be
                              uploaded to this event folder.
                            </Copy>
                            <ScrollView
                              horizontal
                              contentContainerStyle={{ gap: 10 }}
                            >
                              {uploads.map((file) => (
                                <Image
                                  key={file.uri}
                                  source={{ uri: file.uri }}
                                  style={{
                                    width: 90,
                                    height: 110,
                                    borderRadius: 10,
                                  }}
                                />
                              ))}
                            </ScrollView>
                          </>
                        )}
                        <Copy>
                          {gallerySync?.last_success_at
                            ? `Last synchronized: ${new Date(gallerySync.last_success_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}`
                            : "Waiting for the first background synchronization."}
                        </Copy>
                        {!!gallerySync?.error && (
                          <Text style={{ color: "#DA6174", fontSize: 13 }}>
                            {gallerySync.error}
                          </Text>
                        )}
                        <Copy>
                          Drive additions and changes appear after background
                          synchronization. Removing a photograph here moves its
                          original to Drive Trash.
                        </Copy>
                      </Panel>
                    </>
                  )}
                  {(section === "Posts" || section === "Moments") && (
                    <View style={u.row}>
                      <Button onPress={newPublication}>
                        + Create {section === "Posts" ? "post" : "moment"}
                      </Button>
                    </View>
                  )}
                  {(section === "Posts" ||
                    section === "Moments" ||
                    (section === "Gallery" && gallery)) &&
                    publications.map((item) => (
                      <Panel key={item.id}>
                        <View style={u.row}>
                          {cover(item.cover_preview_url || item.cover_url)}
                          <View style={{ flex: 1, gap: 6 }}>
                            {smallTitle(item.title)}
                            <Copy>
                              {item.event_title} · {item.tag}
                            </Copy>
                            <Copy>
                              {item.published && item.available
                                ? "Published"
                                : "Draft / unavailable"}
                            </Copy>
                          </View>
                          <View
                            style={{
                              flexDirection: "row",
                              alignItems: "center",
                              gap: 8,
                            }}
                          >
                            <Button
                              compact
                              secondary
                              label="Edit publication"
                              onPress={() => editPublication(item)}
                            >
                              <Feather name="edit-2" size={14} />
                            </Button>
                            {item.kind !== "photo" && (
                              <Button
                                compact
                                secondary
                                busy={busy}
                                label={
                                  item.published ? "Move to drafts" : "Publish"
                                }
                                onPress={() => togglePublication(item)}
                              >
                                <Feather
                                  name={item.published ? "eye-off" : "upload"}
                                  size={14}
                                />
                              </Button>
                            )}
                            {item.kind === "photo" && (
                              <Button
                                compact
                                secondary
                                danger
                                label="Remove photograph"
                                onPress={() =>
                                  setConfirm({
                                    title: "Remove this photograph?",
                                    detail:
                                      "The original moves to Drive Trash and disappears from this event gallery. It can be restored in Drive.",
                                    action: async () => {
                                      await api(
                                        `/management/publications/${item.id}/`,
                                        { method: "DELETE" },
                                      );
                                      await load();
                                    },
                                  })
                                }
                              >
                                <Feather name="trash-2" size={14} />
                              </Button>
                            )}
                          </View>
                        </View>
                        {!!item.caption && <Copy>{item.caption}</Copy>}
                      </Panel>
                    ))}
                  {section === "Members" && (
                    <>
                      <Field
                        label="Find a member"
                        value={query}
                        onChange={setQuery}
                        placeholder="Username, name or college email"
                        search
                      />
                      {members.map((member) => (
                        <Panel key={member.id}>
                          <View
                            style={{
                              flexDirection: "row",
                              alignItems: "center",
                              gap: 12,
                            }}
                          >
                            <View style={{ flex: 1, minWidth: 0 }}>
                              {smallTitle(
                                member.display_name ||
                                  member.username ||
                                  member.email,
                              )}
                              <Copy>
                                @{member.username || "onboarding"} ·{" "}
                                {member.email}
                              </Copy>
                            </View>
                            <Button
                              compact
                              secondary
                              onPress={() =>
                                setConfirm({
                                  title: member.is_active
                                    ? "Suspend this member?"
                                    : "Restore this member?",
                                  detail:
                                    "Suspended members cannot access PIXEL. Existing content and audit records are retained.",
                                  action: async () => {
                                    await api(
                                      `/management/members/${member.id}/`,
                                      {
                                        method: "PATCH",
                                        body: JSON.stringify({
                                          is_active: !member.is_active,
                                        }),
                                      },
                                    );
                                    await load();
                                  },
                                })
                              }
                            >
                              {member.is_active ? "Suspend" : "Restore"}
                            </Button>
                          </View>
                          <Copy>
                            {member.department} ·{" "}
                            {member.email_verified
                              ? "Verified"
                              : "Not verified"}
                          </Copy>
                          <View style={u.row}>
                            {member.can_set_password && (
                              <Button
                                compact
                                secondary
                                onPress={() => setPasswordMember(member)}
                              >
                                {member.has_password
                                  ? "Change password"
                                  : "Set password"}
                              </Button>
                            )}
                            {["Student", "Faculty", "Administrator"].map(
                              (role) => (
                                <Chip
                                  compact
                                  key={role}
                                  selected={member.role === role}
                                  onPress={() =>
                                    setConfirm({
                                      title: `Set role to ${role}?`,
                                      detail: `This changes access for ${member.display_name || member.email}. Administrator access includes publishing and member management.`,
                                      action: async () => {
                                        await api(
                                          `/management/members/${member.id}/`,
                                          {
                                            method: "PATCH",
                                            body: JSON.stringify({ role }),
                                          },
                                        );
                                        await load();
                                      },
                                    })
                                  }
                                >
                                  {role}
                                </Chip>
                              ),
                            )}
                          </View>
                        </Panel>
                      ))}
                    </>
                  )}
                  {section === "Comments" && (
                    <CommentModeration
                      dark={dark}
                      reloadKey={commentRevision}
                      requestDelete={(comment, done) =>
                        setConfirm({
                          title: "Delete this comment?",
                          detail:
                            "This permanently removes the comment and all replies beneath it.",
                          action: async () => {
                            await api(`/management/comments/${comment.id}/`, {
                              method: "DELETE",
                            });
                            done();
                          },
                        })
                      }
                    />
                  )}
                  {section === "Storage" && storage && (
                    <>
                      <Panel>
                        <Heading eyebrow="GOOGLE DRIVE">
                          {storage.connected
                            ? "Pixel is connected."
                            : "Connect your Pixel account."}
                        </Heading>
                        <Copy>
                          Uploads use the Pixel account. Connection details stay
                          on the server.
                        </Copy>
                        <Button
                          secondary
                          onPress={() =>
                            void Linking.openURL(storage.connect_url)
                          }
                        >
                          Reconnect Pixel Drive ↗
                        </Button>
                      </Panel>
                      <Panel>
                        <Field
                          label="Posts folder"
                          value={postFolder}
                          onChange={setPostFolder}
                          placeholder="Paste the Drive folder link"
                        />
                        <Button
                          busy={busy}
                          onPress={() =>
                            void run(async () => {
                              applyStorage(
                                await api<Storage>("/management/storage/", {
                                  method: "PATCH",
                                  body: JSON.stringify({
                                    kind: "post",
                                    folder_id: postFolder,
                                  }),
                                }),
                              );
                              setMessage("Posts folder saved.");
                            })
                          }
                        >
                          Save Posts folder
                        </Button>
                        <Field
                          label="Moments folder"
                          value={momentFolder}
                          onChange={setMomentFolder}
                          placeholder="Paste the Drive folder link"
                        />
                        <Button
                          busy={busy}
                          onPress={() =>
                            void run(async () => {
                              applyStorage(
                                await api<Storage>("/management/storage/", {
                                  method: "PATCH",
                                  body: JSON.stringify({
                                    kind: "moment",
                                    folder_id: momentFolder,
                                  }),
                                }),
                              );
                              setMessage("Moments folder saved.");
                            })
                          }
                        >
                          Save Moments folder
                        </Button>
                        <Copy>
                          Automatic two-way synchronization applies to event
                          galleries. Posts and moments are published from their
                          own editors.
                        </Copy>
                      </Panel>
                    </>
                  )}
                  {loading &&
                    !refreshing &&
                    section !== "Comments" &&
                    !(section === "Overview" && summary) &&
                    !(section === "Storage" && storage) &&
                    !events.length &&
                    !publications.length &&
                    !members.length && (
                      <ContentSkeleton
                        dark={dark}
                        kind={section === "Overview" ? "overview" : "list"}
                      />
                    )}
                  {!loading &&
                    section !== "Overview" &&
                    section !== "Storage" &&
                    section !== "Comments" &&
                    !events.length &&
                    !publications.length &&
                    !members.length && (
                      <Panel>
                        <Copy>
                          Nothing here yet. Create your first item to bring this
                          section to life.
                        </Copy>
                      </Panel>
                    )}
                  {next &&
                    section !== "Overview" &&
                    section !== "Storage" &&
                    section !== "Comments" && (
                      <Button
                        secondary
                        busy={busy}
                        onPress={() =>
                          void run(async () =>
                            applyPage(
                              await api<
                                Page<
                                  | AdminEvent
                                  | AdminPublication
                                  | AdminMember
                                  | ModerationComment
                                >
                              >(next.replace(`${API_URL}/api/v1`, "")),
                              true,
                            ),
                          )
                        }
                      >
                        Load more
                      </Button>
                    )}
                </>
              )}
            </RefreshScrollView>
          </View>

          {passwordMember && (
            <MemberPasswordDialog
              key={passwordMember.id}
              member={passwordMember}
              close={() => setPasswordMember(null)}
              onSaved={(updated) => {
                setMembers((old) =>
                  old.map((member) =>
                    member.id === updated.id ? updated : member,
                  ),
                );
                setPasswordMember(null);
                setError("");
                setMessage("Password saved. The member must sign in again.");
              }}
            />
          )}
          {confirm && (
            <Modal
              visible
              transparent
              animationType="fade"
              onRequestClose={() => setConfirm(null)}
            >
              <View
                pointerEvents="box-none"
                style={{
                  flex: 1,
                  backgroundColor: "#000000AA",
                  justifyContent: "center",
                  padding: 24,
                }}
              >
                <View
                  style={{ width: "100%", maxWidth: 480, alignSelf: "center" }}
                >
                  <Panel>
                    <Heading>{confirm.title}</Heading>
                    <Copy>{confirm.detail}</Copy>
                    <View style={u.row}>
                      <Button secondary onPress={() => setConfirm(null)}>
                        Cancel
                      </Button>
                      <Button
                        busy={busy}
                        onPress={() =>
                          void run(async () => {
                            await confirm.action();
                            setConfirm(null);
                          })
                        }
                      >
                        Confirm
                      </Button>
                    </View>
                    {!!error && (
                      <Text style={{ color: "#DA6174" }}>{error}</Text>
                    )}
                  </Panel>
                </View>
              </View>
            </Modal>
          )}
        </LiquidPage>
      </Modal>
    </AdminAppearance.Provider>
  );
}
