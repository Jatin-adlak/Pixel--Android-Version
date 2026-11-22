import PostCarousel from "./PostCarousel";
import SavedPublicationGrid from "./SavedPublicationGrid";
import Modal from "../pixel/AppModal";
import { Feather } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  FlatList,
  Image,
  Linking,
  Platform,
  Pressable,
  Share,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { api, API_URL } from "../auth/api";
import { useAuth } from "../auth/AuthProvider";
import { palette, type Tab } from "../pixel/data";
import MomentsScreen from "../pixel/MomentsScreen";
import ProfileHeader from "../pixel/ProfileHeader";
import BackNavigation from "../pixel/BackNavigation";
import RefreshScrollView from "../pixel/RefreshScrollView";
import DesignedButton from "../pixel/DesignedButton";
import MomentActions from "./MomentActions";
import PhotoViewer from "./PhotoViewer";
import MemberRow from "./MemberRow";
import PageHeader from "../pixel/PageHeader";
import LoadingImage from "../pixel/loading/LoadingImage";
import { ContentSkeleton, PixelMotionLoader } from "../pixel/loading/Loading";
import LiquidPage from "../pixel/LiquidPage";
import EventDetails from "./EventDetails";
import FaceSearchControl from "./FaceSearchControl";
import PostActions from "./PostActions";
import PrivatePictures from "./PrivatePictures";
import type {
  CampusEvent,
  Discussion,
  Member,
  Page,
  Person,
  Publication,
} from "./types";

type ButtonProps = {
  label: string;
  onPress: () => void;
  selected?: boolean;
  compact?: boolean;
  stretch?: boolean;
};
function Button({
  label,
  onPress,
  selected,
  compact,
  stretch,
  busy,
}: ButtonProps & { dark: boolean; busy: boolean }) {
  return (
    <DesignedButton
      onPress={onPress}
      selected={selected}
      compact={compact}
      stretch={stretch}
      disabled={busy}
      label={label}
    >
      {label}
    </DesignedButton>
  );
}

export default function ContentScreen({
  tab,
  dark,
  height,
  onEdit,
  onAdmin,
  inbox = 0,
}: {
  tab: Tab;
  dark: boolean;
  height: number;
  onEdit: () => void;
  onAdmin?: () => void;
  inbox?: number;
}) {
  const theme = dark ? palette.dark : palette.light;
  const { user } = useAuth();
  const shared = useLocalSearchParams<{ publication?: string }>();
  const [items, setItems] = useState<Publication[]>([]);
  const [events, setEvents] = useState<CampusEvent[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [listingCount, setListingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [momentsHeight, setMomentsHeight] = useState(height);
  const [savedMomentHeight, setSavedMomentHeight] = useState(height);
  const [refreshing, setRefreshing] = useState(false);
  const loadRequest = useRef<AbortController | null>(null);
  const [error, setError] = useState("");
  const [event, setEvent] = useState<CampusEvent | null>(null);
  const [faceResults, setFaceResults] = useState<{
    eventId: string;
    path: string;
  } | null>(null);
  const [photo, setPhoto] = useState<Publication | null>(null);
  const [openedPost, setOpenedPost] = useState<Publication | null>(null);
  const [postImage, setPostImage] = useState(0);
  const [discussion, setDiscussion] = useState<Publication | null>(null);
  const [comments, setComments] = useState<Discussion[]>([]);
  const [commentNext, setCommentNext] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [reply, setReply] = useState<Discussion | null>(null);
  const [section, setSection] = useState("post");
  const [filter, setFilter] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filterLabel, setFilterLabel] = useState("All moments");
  const [filterEvents, setFilterEvents] = useState<CampusEvent[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const operation = useRef(false);
  const [people, setPeople] = useState<Person[]>([]);
  const [member, setMember] = useState<Member | null>(null);
  const [memberLoading, setMemberLoading] = useState(false);
  const [connections, setConnections] = useState<
    { id: number; user: Person; mandatory: boolean }[]
  >([]);
  const [connectionKind, setConnectionKind] = useState("");
  const [connectionsRefreshing, setConnectionsRefreshing] = useState(false);
  const [connectionNext, setConnectionNext] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [own, setOwn] = useState<Member | null>(null);
  useEffect(() => {
    if (!shared.publication || !/^[0-9a-f-]{36}$/i.test(shared.publication))
      return;
    void api<Publication>(`/publications/${shared.publication}/`)
      .then((item) =>
        item.kind === "post" ? setOpenedPost(item) : setPhoto(item),
      )
      .catch((e) => setError(e.message));
  }, [shared.publication]);
  useEffect(() => {
    if (!inbox) return;
    void api<Page<{ id: number; user: Person; mandatory: boolean }>>(
      "/connections/?kind=requests",
    )
      .then((p) => {
        setConnectionKind("requests");
        setConnections(p.results);
        setConnectionNext(p.next);
      })
      .catch((e) => setError(e.message));
  }, [inbox]);
  const isProfile = !event && (tab === "Profile" || !!member);
  const momentsFeed = tab === "Moments" && !event && !isProfile;
  const username = member?.username || user?.username;

  const run = async (work: () => Promise<void>) => {
    if (operation.current) return;
    operation.current = true;
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      operation.current = false;
      setBusy(false);
    }
  };
  const path = useCallback(
    (searchTerm = "") => {
      if (event && faceResults?.eventId === event.id) return faceResults.path;
      if (isProfile) return `/members/${username}/saved/?kind=${section}`;
      if (tab === "Gallery" && !event)
        return `/events/?q=${encodeURIComponent(searchTerm)}${category === "All" ? "" : `&tag=${encodeURIComponent(category)}`}`;
      if (tab === "Spotlight" && !event) return "/spotlights/";
      return `/feed/?kind=${event ? "photo" : tab === "Moments" ? "moment" : "post"}${event ? `&event_id=${event.id}` : ""}${filter}`;
    },
    [isProfile, username, section, tab, event, filter, category, faceResults],
  );
  const load = useCallback(
    async (searchTerm = "", refresh = false) => {
      loadRequest.current?.abort();
      const controller = new AbortController();
      loadRequest.current = controller;
      setRefreshing(refresh);
      setLoading(true);
      setError("");
      if (!refresh) {
        setItems([]);
        setEvents([]);
        setNext(null);
      }
      try {
        if (
          (tab === "Gallery" || tab === "Spotlight") &&
          !event &&
          !isProfile
        ) {
          const page = await api<Page<CampusEvent>>(path(searchTerm), {
            signal: controller.signal,
          });
          if (controller.signal.aborted) return;
          setEvents(page.results);
          setNext(page.next);
        } else if (
          !(tab === "Spotlight" && event) &&
          !(
            isProfile &&
            section === "photo" &&
            member &&
            !member.can_see_photos
          )
        ) {
          const page = await api<Page<Publication>>(path(), {
            signal: controller.signal,
          });
          if (controller.signal.aborted) return;
          setItems(page.results);
          setListingCount(page.count ?? page.results.length);
          setNext(page.next);
        }
        if (user?.username) {
          const profile = await api<Member>(`/members/${user.username}/`, {
            signal: controller.signal,
          });
          if (!controller.signal.aborted) setOwn(profile);
        }
      } catch (e) {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Could not load.");
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [path, tab, event, isProfile, section, member, user],
  );
  useEffect(() => {
    let active = true;
    void Promise.resolve().then(() => {
      if (active) void load();
    });
    return () => {
      active = false;
      loadRequest.current?.abort();
    };
  }, [load]);
  useEffect(() => {
    if (tab !== "Gallery" || event || isProfile) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void api<Page<CampusEvent>>(path(query.trim()), {
        signal: controller.signal,
      })
        .then((page) => {
          if (!controller.signal.aborted) {
            setEvents(page.results);
            setNext(page.next);
          }
        })
        .catch((error) => {
          if (!controller.signal.aborted) setError(error.message);
        });
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, tab, event, isProfile, path]);
  useEffect(() => {
    if (tab !== "Spotlight" || query.trim().length < 2) {
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      void api<Page<Person>>(`/users/?q=${encodeURIComponent(query)}`, {
        signal: controller.signal,
      })
        .then((p) => setPeople(p.results))
        .catch((e) => {
          if (!controller.signal.aborted) setError(e.message);
        });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, tab]);

  const update = (value: Publication) => {
    const social = {
      liked: value.liked,
      saved: value.saved,
      like_count: value.like_count,
      comment_count: value.comment_count,
    };
    const ownCollection = isProfile && (!member || member.id === user?.id);
    const previous =
      items.find((item) => item.id === value.id) ||
      (openedPost?.id === value.id
        ? openedPost
        : photo?.id === value.id
          ? photo
          : null);
    setItems((old) => {
      if (ownCollection && !value.saved)
        return old.filter((item) => item.id !== value.id);
      if (
        ownCollection &&
        value.saved &&
        !old.some((item) => item.id === value.id) &&
        value.kind === section
      )
        return [value, ...old];
      return old.map((item) =>
        item.id === value.id ? { ...item, ...social } : item,
      );
    });
    if (ownCollection && previous && previous.saved !== value.saved)
      setOwn((old) =>
        old
          ? {
              ...old,
              saved_count: Math.max(
                0,
                (old.saved_count || 0) + (value.saved ? 1 : -1),
              ),
            }
          : old,
      );
    setPhoto((old) => (old?.id === value.id ? { ...old, ...social } : old));
    setOpenedPost((old) =>
      old?.id === value.id ? { ...old, ...social } : old,
    );
    setDiscussion((old) =>
      old?.id === value.id ? { ...old, ...social } : old,
    );
  };
  const react = (item: Publication, action: "like" | "save") =>
    void run(async () =>
      update(
        await api<Publication>(`/publications/${item.id}/${action}/`, {
          method: (action === "like" ? item.liked : item.saved)
            ? "DELETE"
            : "PUT",
        }),
      ),
    );
  const openMember = (person: Person) =>
    void run(async () => {
      setMemberLoading(true);
      setConnectionKind("");
      setDiscussion(null);
      setPhoto(null);
      setOpenedPost(null);
      try {
        setMember(await api<Member>(`/members/${person.username}/`));
        setEvent(null);
        setFaceResults(null);
        setSection("post");
      } finally {
        setMemberLoading(false);
      }
    });
  const more = () =>
    void run(async () => {
      if (!next) return;
      const relative = next.replace(`${API_URL}/api/v1`, "");
      if ((tab === "Gallery" || tab === "Spotlight") && !event && !isProfile) {
        const page = await api<Page<CampusEvent>>(relative);
        setEvents((old) => [...old, ...page.results]);
        setNext(page.next);
      } else {
        const page = await api<Page<Publication>>(relative);
        setItems((old) => [...old, ...page.results]);
        setNext(page.next);
      }
    });
  const openComments = (item: Publication) =>
    void run(async () => {
      setDiscussion(item);
      setComments([]);
      setCommentNext(null);
      const page = await api<Page<Discussion>>(
        `/publications/${item.id}/comments/`,
      );
      setComments(page.results);
      setCommentNext(page.next);
    });
  const refreshComments = async () => {
    if (!discussion) return;
    const page = await api<Page<Discussion>>(
      `/publications/${discussion.id}/comments/`,
    );
    setComments(page.results);
    setCommentNext(page.next);
    update(await api<Publication>(`/publications/${discussion.id}/`));
  };
  const download = (item: Publication, image?: number) =>
    void run(async () => {
      const result = await api<{ url: string }>(
        `/publications/${item.id}/download/${image !== undefined ? `?image=${image}` : ""}`,
      );
      await Linking.openURL(result.url);
    });
  const body = (value: string) => (
    <Text style={[s.body, { color: theme.muted }]}>{value}</Text>
  );
  const title = (value: string) => (
    <Text style={[s.title, { color: theme.text }]}>{value}</Text>
  );
  const identity = (person: Person) => (
    <MemberRow person={person} dark={dark} onPress={() => openMember(person)} />
  );
  const openEvent = (item: Publication) =>
    void run(async () => {
      const found = await api<CampusEvent>(`/events/${item.event_id}/`);
      setMember(null);
      setEvent(found);
      setFaceResults(null);
      setPhoto(null);
      setOpenedPost(null);
      setDiscussion(null);
      setMember(null);
    });
  const shareItem = (item: Publication) =>
    void run(async () => {
      const url = `${process.env.EXPO_PUBLIC_WEB_URL || "http://localhost:8081"}/?publication=${item.id}`;
      if (Platform.OS === "web" && !navigator.share) {
        await navigator.clipboard.writeText(url);
        setError("Link copied.");
      } else await Share.share({ message: `${item.title} — ${url}`, url });
    });
  const actions = (item: Publication, video = false) =>
    video ? (
      <MomentActions
        item={item}
        like={() => react(item, "like")}
        comment={() => openComments(item)}
        share={() => shareItem(item)}
        save={() => react(item, "save")}
        download={() => download(item)}
        event={() => openEvent(item)}
      />
    ) : (
      <PostActions
        item={item}
        dark={dark}
        like={() => react(item, "like")}
        comment={() => openComments(item)}
        share={() => shareItem(item)}
        save={() => react(item, "save")}
        event={() => openEvent(item)}
        download={item.kind === "moment" ? () => download(item) : undefined}
      />
    );
  const renderPublication = (item: Publication, expanded = false) => (
    <View style={{ marginBottom: 26 }}>
      <Pressable
        onPress={() => openMember(item.author)}
        style={[s.row, { height: 62 }]}
      >
        {item.author.avatar_url ? (
          <Image source={{ uri: item.author.avatar_url }} style={s.avatar} />
        ) : (
          <View
            style={[
              s.avatar,
              {
                backgroundColor: theme.surface,
                alignItems: "center",
                justifyContent: "center",
              },
            ]}
          >
            <Text style={{ color: palette.blue, fontWeight: "800" }}>p.</Text>
          </View>
        )}
        <View style={{ flex: 1, gap: 3 }}>
          <Text style={{ color: theme.text, fontSize: 14, fontWeight: "600" }}>
            @{item.author.username}
          </Text>
          <Text style={{ color: theme.muted, fontSize: 11 }}>
            Campus · {new Date(item.created_at).toLocaleDateString()}
          </Text>
        </View>
      </Pressable>
      <PostCarousel
        item={item}
        dark={dark}
        open={(index) => {
          setPostImage(index);
          setPhoto(item);
        }}
      />
      {actions(item)}
      <Text style={{ color: theme.text, fontSize: 14, fontWeight: "600" }}>
        {item.like_count} likes
      </Text>
      <Text
        numberOfLines={expanded ? undefined : 2}
        style={{
          color: theme.text,
          fontSize: 14,
          lineHeight: 21,
          marginTop: 6,
        }}
      >
        <Text style={{ fontWeight: "700" }}>@{item.author.username} </Text>
        {item.caption}
      </Text>
      <Pressable onPress={() => openComments(item)}>
        <Text style={{ color: theme.muted, fontSize: 11, marginTop: 8 }}>
          View comments ({item.comment_count})
        </Text>
      </Pressable>
    </View>
  );
  const photoPosition = photo
    ? items.findIndex((item) => item.id === photo.id)
    : -1;
  const previousPhoto = () => {
    if (photoPosition > 0) setPhoto(items[photoPosition - 1]);
  };
  const nextPhoto = () => {
    if (photoPosition >= 0 && photoPosition + 1 < items.length) {
      setPhoto(items[photoPosition + 1]);
      return;
    }
    if (next && photoPosition >= 0)
      void run(async () => {
        const page = await api<Page<Publication>>(
          next.replace(`${API_URL}/api/v1`, ""),
        );
        setItems((old) => [...old, ...page.results]);
        setNext(page.next);
        if (page.results[0]) setPhoto(page.results[0]);
      });
  };
  const returnToFeed = useCallback(() => {
    setEvent(null);
    setFaceResults(null);
    setMember(null);
    setSection("post");
  }, []);
  const viewProfile = member || own;
  const loadConnections = (kind: string) =>
    run(async () => {
      setConnectionKind(kind);
      if (!connectionsRefreshing) {
        setConnections([]);
        setConnectionNext(null);
      }
      const p = await api<
        Page<{ id: number; user: Person; mandatory: boolean }>
      >(`/connections/?kind=${kind}`);
      setConnections(p.results);
      setConnectionNext(p.next);
    });

  return (
    <View
      style={{ flex: 1, backgroundColor: theme.background }}
      onLayout={(e) => setMomentsHeight(e.nativeEvent.layout.height)}
    >
      {!!error && (
        <Pressable onPress={() => setError("")} style={s.notice}>
          <Text style={{ color: "#DA6174" }}>{error}</Text>
        </Pressable>
      )}
      <RefreshScrollView
        refreshing={refreshing}
        enabled={!momentsFeed && !busy && (!loading || refreshing)}
        onRefresh={() => void load(query, true)}
        dark={dark}
        contentContainerStyle={{
          padding: momentsFeed ? 0 : 16,
          paddingBottom: momentsFeed ? 0 : 120,
          gap: momentsFeed ? 0 : 18,
        }}
        scrollEnabled={!momentsFeed}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {(event || member) && <BackNavigation onPress={returnToFeed} />}
        {isProfile && viewProfile && (
          <>
            <ProfileHeader
              dark={dark}
              savedCount={viewProfile.saved_count ?? items.length}
              profile={viewProfile}
              own={!member || member.id === user?.id}
              onEdit={onEdit}
              onHeight={() => {}}
              onError={setError}
              onFollowers={() => loadConnections("followers")}
              onFollowing={() => loadConnections("following")}
            />
            {!member || member.id === user?.id ? (
              <>
                {user?.role === "Administrator" &&
                  viewProfile.role === "Administrator" && (
                    <Button
                      dark={dark}
                      busy={busy}
                      label="Admin dashboard"
                      onPress={() => onAdmin?.()}
                    />
                  )}
              </>
            ) : (
              <Button
                dark={dark}
                busy={busy || member.mandatory}
                selected={member.follow_state === "accepted"}
                label={
                  member.mandatory
                    ? "Following Pixel"
                    : member.follow_state === "accepted"
                      ? "Unfollow"
                      : member.follow_state === "pending"
                        ? "Cancel request"
                        : "Follow"
                }
                onPress={() =>
                  void run(async () =>
                    setMember(
                      await api<Member>(`/members/${member.username}/follow/`, {
                        method:
                          member.follow_state === "none" ? "PUT" : "DELETE",
                      }),
                    ),
                  )
                }
              />
            )}
            <View style={[s.row, { alignItems: "stretch" }]}>
              {[
                ["photo", "Saved pictures"],
                ["post", "Saved posts"],
                ["moment", "Saved moments"],
              ].map(([kind, label]) => (
                <View key={kind} style={{ flex: 1, minWidth: 0 }}>
                  <Button
                    dark={dark}
                    busy={busy}
                    label={label}
                    stretch
                    selected={section === kind}
                    onPress={() => setSection(kind)}
                  />
                </View>
              ))}
            </View>
            {member && section === "photo" && !member.can_see_photos && (
              <PrivatePictures dark={dark} />
            )}
          </>
        )}
        {(tab === "Gallery" || tab === "Spotlight") && !event && !isProfile && (
          <View
            style={[
              s.search,
              { borderWidth: 0, backgroundColor: theme.surface },
            ]}
          >
            <Feather name="search" color={theme.muted} size={19} />
            <TextInput
              testID="pixel-search-input"
              accessibilityLabel={
                tab === "Spotlight" ? "Search usernames" : "Search events"
              }
              placeholder={
                tab === "Spotlight"
                  ? "Find people on campus"
                  : "Find your next memory"
              }
              placeholderTextColor={theme.muted}
              value={query}
              onChangeText={setQuery}
              style={[
                s.searchInput,
                { color: theme.text },
                Platform.OS === "web" ? { outlineWidth: 0 } : undefined,
              ]}
              autoCapitalize="none"
            />
            {!!query && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Clear search"
                onPress={() => setQuery("")}
                style={{
                  width: 36,
                  height: 44,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Feather name="x" size={18} color={theme.muted} />
              </Pressable>
            )}
          </View>
        )}
        {tab === "Gallery" && !event && !isProfile && (
          <View style={{ flexDirection: "row", gap: 8 }}>
            {["All", "Cultural", "Sports", "Technical"].map((value) => (
              <View key={value} style={{ flex: 1 }}>
                <Button
                  dark={dark}
                  busy={busy}
                  label={value}
                  selected={category === value}
                  onPress={() => setCategory(value)}
                />
              </View>
            ))}
          </View>
        )}
        {!!people.length &&
          query.trim().length >= 2 &&
          tab === "Spotlight" &&
          !member && (
            <View
              style={[
                s.card,
                { borderColor: theme.line, backgroundColor: theme.surface },
              ]}
            >
              {people.map((person) => (
                <View key={person.id}>{identity(person)}</View>
              ))}
            </View>
          )}
        {event && (
          <EventDetails
            event={event}
            dark={dark}
            spotlight={tab === "Spotlight"}
          />
        )}
        {event && tab !== "Spotlight" && (
          <FaceSearchControl
            key={event.id}
            eventId={event.id}
            dark={dark}
            onResults={(path) =>
              setFaceResults(path ? { eventId: event.id, path } : null)
            }
          />
        )}
        {momentsFeed && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Filter moments"
            onPress={() => {
              setFiltersOpen(true);
              void run(async () => {
                let url: string | null = "/events/";
                const choices: CampusEvent[] = [];
                while (url) {
                  const page: Page<CampusEvent> =
                    await api<Page<CampusEvent>>(url);
                  choices.push(...page.results);
                  url = page.next?.replace(`${API_URL}/api/v1`, "") || null;
                }
                setFilterEvents(choices);
              });
            }}
            style={{
              position: "absolute",
              top: 8,
              zIndex: 2,
              alignSelf: "center",
              flexDirection: "row",
              alignItems: "center",
              gap: 6,
              paddingVertical: 8,
              paddingHorizontal: 12,
            }}
          >
            <Text
              style={{
                color: palette.ivory,
                fontSize: 15,
                fontWeight: "600",
                textShadowColor: "#000000CC",
                textShadowRadius: 6,
                textShadowOffset: { width: 0, height: 1 },
              }}
            >
              {filterLabel}
            </Text>
            <Feather name="chevron-down" size={15} color={palette.ivory} />
          </Pressable>
        )}
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
          {events.map((item) => (
            <View
              key={item.id}
              style={{
                width: tab === "Gallery" ? "48%" : "100%",
                marginBottom: tab === "Gallery" ? 4 : 18,
              }}
            >
              <View
                style={{
                  backgroundColor: palette.blue,
                  marginLeft: 4,
                  marginTop: 5,
                }}
              >
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={`Open ${item.title}`}
                  onPress={() => {
                    setFaceResults(null);
                    setEvent(item);
                  }}
                  style={{
                    borderWidth: 3,
                    borderColor: palette.charcoal,
                    backgroundColor: palette.ivory,
                    transform: [{ translateX: -4 }, { translateY: -5 }],
                  }}
                >
                  <LoadingImage
                    dark={dark}
                    source={{ uri: item.cover_url }}
                    style={
                      tab === "Gallery"
                        ? { width: "100%", aspectRatio: 1.06 }
                        : { width: "100%", height: 220 }
                    }
                    resizeMode="cover"
                  />
                  <View
                    style={{
                      position: "absolute",
                      top: 12,
                      left: 12,
                      borderRadius: 20,
                      borderWidth: 2,
                      borderColor: palette.charcoal,
                      backgroundColor: palette.blue,
                      paddingVertical: 5,
                      paddingHorizontal: 8,
                    }}
                  >
                    <Text
                      style={{
                        color: palette.ivory,
                        fontSize: 9,
                        fontWeight: "800",
                      }}
                    >
                      {tab === "Spotlight"
                        ? "UPCOMING"
                        : item.tag.toUpperCase()}
                    </Text>
                  </View>
                  <View
                    style={{
                      height: 66,
                      padding: 12,
                      borderTopWidth: 3,
                      borderTopColor: palette.charcoal,
                    }}
                  >
                    <Text
                      numberOfLines={1}
                      style={{
                        color: palette.charcoal,
                        fontSize: 13,
                        fontWeight: "700",
                      }}
                    >
                      {item.title}
                    </Text>
                    <Text
                      style={{ color: "#646B77", fontSize: 10, marginTop: 5 }}
                    >
                      {tab === "Gallery"
                        ? `${item.photo_count ?? 0} photos`
                        : new Date(item.starts_at).toLocaleDateString()}
                    </Text>
                  </View>
                </Pressable>
              </View>
              {tab === "Spotlight" && (
                <Text
                  numberOfLines={2}
                  style={{
                    color: theme.muted,
                    fontSize: 14,
                    lineHeight: 21,
                    marginTop: 12,
                  }}
                >
                  {item.description}
                </Text>
              )}
            </View>
          ))}
        </View>
        {momentsFeed ? (
          <View style={{ height: momentsHeight }}>
            {loading && !items.length ? (
              <PixelMotionLoader dark overlay />
            ) : (
              <MomentsScreen
                clips={items}
                height={momentsHeight}
                renderActions={(clip) => {
                  const item = items.find((p) => p.id === clip.id);
                  return item ? actions(item, true) : null;
                }}
              />
            )}
          </View>
        ) : isProfile && (section === "post" || section === "moment") ? (
          <SavedPublicationGrid
            items={items}
            dark={dark}
            open={(item) => {
              setError("");
              setPostImage(0);
              if (item.kind === "post") setOpenedPost(item);
              else setPhoto(item);
            }}
          />
        ) : event || (isProfile && section === "photo") ? (
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
            {items.map((item) => (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`View ${item.title}`}
                key={item.id}
                onPress={() => setPhoto(item)}
                style={{
                  width: "48%",
                  borderWidth: 0,
                  borderColor: palette.charcoal,
                  backgroundColor: palette.blue,
                }}
              >
                <View
                  style={{
                    marginLeft: 4,
                    marginTop: 5,
                    backgroundColor: palette.blue,
                  }}
                >
                  <LoadingImage
                    dark={dark}
                    source={{ uri: item.cover_url }}
                    style={{
                      width: "100%",
                      aspectRatio: 1 / 1.22,
                      borderWidth: 3,
                      borderColor: palette.charcoal,
                      transform: [{ translateX: -4 }, { translateY: -5 }],
                    }}
                    resizeMode="cover"
                  />
                </View>
              </Pressable>
            ))}
          </View>
        ) : (
          items.map((item) => (
            <View key={item.id}>{renderPublication(item)}</View>
          ))
        )}
        {loading &&
          !refreshing &&
          !momentsFeed &&
          !items.length &&
          !events.length &&
          !(tab === "Spotlight" && event) &&
          !(
            isProfile &&
            member &&
            section === "photo" &&
            !member.can_see_photos
          ) && (
            <ContentSkeleton
              dark={dark}
              kind={
                isProfile && !viewProfile
                  ? "profile"
                  : tab === "Home"
                    ? "post"
                    : "cards"
              }
            />
          )}
        {!loading &&
          !items.length &&
          !events.length &&
          !error &&
          !(event && faceResults?.eventId === event.id) &&
          !(
            isProfile &&
            section === "photo" &&
            member &&
            !member.can_see_photos
          ) &&
          tab !== "Moments" &&
          !(tab === "Spotlight" && event) &&
          body("Nothing published here yet.")}
        {next && (
          <Button dark={dark} busy={busy} label="Load more" onPress={more} />
        )}
      </RefreshScrollView>
      {memberLoading && (
        <View
          style={[
            StyleSheet.absoluteFill,
            { backgroundColor: theme.background, padding: 16, zIndex: 5 },
          ]}
        >
          <ContentSkeleton dark={dark} kind="profile" />
        </View>
      )}
      {openedPost && (
        <Modal
          visible
          animationType="none"
          onRequestClose={() => setOpenedPost(null)}
        >
          <LiquidPage
            closeDock={() => setOpenedPost(null)}
            style={{ backgroundColor: theme.background }}
          >
            <PageHeader dark={dark} title="Post" />
            <BackNavigation onPress={() => setOpenedPost(null)} />
            <ScrollView
              contentContainerStyle={{ padding: 16, paddingBottom: 128 }}
            >
              {renderPublication(openedPost, true)}
              {!!error && (
                <Text
                  accessibilityLiveRegion="polite"
                  style={{
                    color: error === "Link copied." ? palette.blue : "#DA6174",
                    fontSize: 13,
                    lineHeight: 20,
                  }}
                >
                  {error}
                </Text>
              )}
            </ScrollView>
          </LiquidPage>
        </Modal>
      )}
      {photo && photo.kind !== "moment" && (
        <PhotoViewer
          photo={photo}
          initialImage={postImage}
          dark={dark}
          busy={busy}
          position={Math.max(0, photoPosition)}
          total={listingCount || items.length || 1}
          previous={previousPhoto}
          next={nextPhoto}
          canPrevious={photoPosition > 0}
          canNext={
            photoPosition >= 0 && (photoPosition + 1 < items.length || !!next)
          }
          save={() => react(photo, "save")}
          download={(image) => download(photo, image)}
          close={() => setPhoto(null)}
        />
      )}
      {photo?.kind === "moment" && (
        <Modal
          visible
          animationType="none"
          onRequestClose={() => setPhoto(null)}
        >
          <LiquidPage
            closeDock={() => setPhoto(null)}
            style={{
              flex: 1,
              backgroundColor: theme.background,
              paddingTop: 0,
            }}
          >
            <PageHeader dark={dark} />
            <BackNavigation onPress={() => setPhoto(null)} />
            <View
              style={{ flex: 1 }}
              onLayout={(event) =>
                setSavedMomentHeight(event.nativeEvent.layout.height)
              }
            >
              <MomentsScreen
                clips={[photo]}
                height={savedMomentHeight}
                renderActions={() => actions(photo, true)}
              />
            </View>
          </LiquidPage>
        </Modal>
      )}
      <Modal
        visible={!!discussion}
        animationType="none"
        onRequestClose={() => setDiscussion(null)}
      >
        <LiquidPage
          closeDock={() => setDiscussion(null)}
          style={{
            flex: 1,
            backgroundColor: theme.background,
            paddingHorizontal: 0,
            paddingBottom: 112,
            paddingTop: 0,
          }}
        >
          <PageHeader dark={dark} title="Comments" />
          <View style={{ paddingHorizontal: 20 }}>
            <BackNavigation
              onPress={() => {
                setDiscussion(null);
                setReply(null);
              }}
            />
          </View>
          <FlatList
            contentContainerStyle={{ paddingHorizontal: 20 }}
            ListEmptyComponent={
              busy ? (
                <ContentSkeleton dark={dark} />
              ) : (
                <Text
                  style={{
                    color: theme.muted,
                    fontSize: 13,
                    paddingVertical: 24,
                  }}
                >
                  Be the first to leave a comment.
                </Text>
              )
            }
            data={comments}
            keyExtractor={(item) => String(item.id)}
            renderItem={({ item }) => (
              <View
                style={[
                  s.comment,
                  {
                    borderColor: theme.line,
                    marginLeft: item.parent_id ? 24 : 0,
                  },
                ]}
              >
                <View
                  style={{ flexDirection: "row", alignItems: "center", gap: 8 }}
                >
                  <View style={{ flex: 1 }}>{identity(item.author)}</View>
                  <View style={{ flexDirection: "row", gap: 8 }}>
                    <Button
                      compact
                      dark={dark}
                      busy={busy}
                      label={`♥ ${item.like_count}`}
                      selected={item.liked}
                      onPress={() =>
                        void run(async () => {
                          const next = await api<Discussion>(
                            item.liked
                              ? `/comments/${item.id}/like/`
                              : `/comments/${item.id}/`,
                            { method: item.liked ? "DELETE" : "PUT" },
                          );
                          setComments((old) =>
                            old.map((c) => (c.id === next.id ? next : c)),
                          );
                        })
                      }
                    />
                    <Button
                      compact
                      dark={dark}
                      busy={busy}
                      label="Reply"
                      onPress={() => setReply(item)}
                    />
                    {item.can_delete && (
                      <Button
                        compact
                        dark={dark}
                        busy={busy}
                        label="Delete"
                        onPress={() =>
                          void run(async () => {
                            await api(`/comments/${item.id}/`, {
                              method: "DELETE",
                            });
                            await refreshComments();
                          })
                        }
                      />
                    )}
                  </View>
                </View>
                {item.parent_id && body(`Reply to comment #${item.parent_id}`)}
                {body(item.text)}
              </View>
            )}
          />
          <View style={{ paddingHorizontal: 20 }}>
            {commentNext && (
              <Button
                dark={dark}
                busy={busy}
                label="More comments"
                onPress={() =>
                  void run(async () => {
                    const p = await api<Page<Discussion>>(
                      commentNext.replace(`${API_URL}/api/v1`, ""),
                    );
                    setComments((old) => [...old, ...p.results]);
                    setCommentNext(p.next);
                  })
                }
              />
            )}
            {reply && (
              <Button
                dark={dark}
                busy={busy}
                label={`Replying to @${reply.author.username} · Cancel`}
                onPress={() => setReply(null)}
              />
            )}
            <TextInput
              placeholder="Add a comment…"
              placeholderTextColor={theme.muted}
              value={text}
              onChangeText={setText}
              maxLength={2000}
              style={[
                s.search,
                {
                  color: theme.text,
                  borderColor: theme.text,
                  marginVertical: 12,
                },
              ]}
            />
            <Button
              dark={dark}
              busy={busy}
              label="Post comment"
              onPress={() =>
                void run(async () => {
                  if (!discussion || !text.trim()) return;
                  await api(`/publications/${discussion.id}/comments/`, {
                    method: "POST",
                    body: JSON.stringify({ text, parent_id: reply?.id }),
                  });
                  setText("");
                  setReply(null);
                  await refreshComments();
                })
              }
            />
            {!!error && body(error)}
          </View>
        </LiquidPage>
      </Modal>
      <Modal
        visible={filtersOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setFiltersOpen(false)}
      >
        <View pointerEvents="box-none" style={s.scrim}>
          <View
            style={[
              s.card,
              { backgroundColor: theme.surface, borderColor: theme.text },
            ]}
          >
            {title("Your moments")}
            <ScrollView
              style={{ maxHeight: 420 }}
              keyboardShouldPersistTaps="handled"
            >
              {[
                { label: "All moments", value: "" },
                ...Array.from(
                  new Set([
                    "Sports",
                    "Cultural",
                    "Technical",
                    ...filterEvents.map((e) => e.tag),
                    ...items.map((i) => i.tag),
                  ]),
                ).map((tag) => ({
                  label: tag,
                  value: `&tag=${encodeURIComponent(tag)}`,
                })),
                ...filterEvents.map((e) => ({
                  label: e.title,
                  value: `&event_id=${e.id}`,
                })),
              ].map((choice) => (
                <Pressable
                  key={choice.value}
                  accessibilityRole="button"
                  accessibilityState={{ selected: filter === choice.value }}
                  onPress={() => {
                    setFilter(choice.value);
                    setFilterLabel(choice.label);
                    setFiltersOpen(false);
                  }}
                  style={{
                    flexDirection: "row",
                    alignItems: "center",
                    justifyContent: "space-between",
                    paddingVertical: 16,
                    borderBottomWidth: 1,
                    borderBottomColor: theme.line,
                  }}
                >
                  <Text
                    style={{
                      color:
                        filter === choice.value ? palette.blue : theme.text,
                      fontSize: 15,
                      fontWeight: filter === choice.value ? "700" : "400",
                    }}
                  >
                    {choice.label}
                  </Text>
                  {filter === choice.value && (
                    <Feather name="check" size={18} color={palette.blue} />
                  )}
                </Pressable>
              ))}
            </ScrollView>
            <Pressable
              accessibilityRole="button"
              onPress={() => setFiltersOpen(false)}
              style={{ alignSelf: "flex-end", padding: 10 }}
            >
              <Text style={{ color: palette.blue, fontSize: 14 }}>Done</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
      <Modal
        visible={!!connectionKind}
        animationType="none"
        onRequestClose={() => setConnectionKind("")}
      >
        <LiquidPage
          closeDock={() => setConnectionKind("")}
          style={{ flex: 1, backgroundColor: theme.background }}
        >
          <PageHeader dark={dark} />
          <RefreshScrollView
            refreshing={connectionsRefreshing}
            enabled={!busy}
            onRefresh={() => {
              setConnectionsRefreshing(true);
              void loadConnections(connectionKind).finally(() =>
                setConnectionsRefreshing(false),
              );
            }}
            dark={dark}
            style={{ backgroundColor: theme.background }}
            contentContainerStyle={{
              padding: 20,
              paddingTop: 12,
              paddingBottom: 120,
              gap: 12,
            }}
          >
            <BackNavigation onPress={() => setConnectionKind("")} />
            {title(connectionKind)}
            {busy && !connections.length && <ContentSkeleton dark={dark} />}
            {!busy && !connections.length && (
              <View
                style={{ paddingVertical: 28, gap: 8, alignItems: "center" }}
              >
                <Feather name="users" size={28} color={theme.muted} />
                <Text style={{ color: theme.muted, fontSize: 14 }}>
                  {connectionKind === "requests"
                    ? "No pending follow requests."
                    : connectionKind === "followers"
                      ? "No followers yet."
                      : "You’re not following anyone yet."}
                </Text>
              </View>
            )}
            {connections.map((c) => (
              <View
                key={c.id}
                style={{ borderBottomWidth: 1, borderBottomColor: theme.line }}
              >
                <MemberRow
                  person={c.user}
                  dark={dark}
                  onPress={() => openMember(c.user)}
                  actions={
                    <>
                      {connectionKind === "requests" && (
                        <Button
                          compact
                          dark={dark}
                          busy={busy}
                          label="Accept"
                          onPress={() =>
                            void run(async () => {
                              await api(`/connections/${c.id}/`, {
                                method: "PUT",
                              });
                              setConnections((old) =>
                                old.filter((item) => item.id !== c.id),
                              );
                              await load();
                            })
                          }
                        />
                      )}
                      {!c.mandatory && (
                        <Button
                          compact
                          dark={dark}
                          busy={busy}
                          label={
                            connectionKind === "requests" ? "Decline" : "Remove"
                          }
                          onPress={() =>
                            void run(async () => {
                              await api(`/connections/${c.id}/`, {
                                method: "DELETE",
                              });
                              setConnections((old) =>
                                old.filter((item) => item.id !== c.id),
                              );
                              await load();
                            })
                          }
                        />
                      )}
                    </>
                  }
                />
              </View>
            ))}
            {connectionNext && (
              <Button
                dark={dark}
                busy={busy}
                label="More"
                onPress={() =>
                  void run(async () => {
                    const p = await api<
                      Page<{ id: number; user: Person; mandatory: boolean }>
                    >(connectionNext.replace(`${API_URL}/api/v1`, ""));
                    setConnections((old) => [...old, ...p.results]);
                    setConnectionNext(p.next);
                  })
                }
              />
            )}
            {!!error && body(error)}
          </RefreshScrollView>
        </LiquidPage>
      </Modal>
    </View>
  );
}
const s = StyleSheet.create({
  card: {
    borderWidth: 2,
    borderRadius: 0,
    padding: 14,
    gap: 14,
    marginBottom: 12,
  },
  cover: { width: "100%", aspectRatio: 0.95, borderRadius: 0 },
  title: { fontSize: 20, fontWeight: "700", letterSpacing: -0.4 },
  body: { fontSize: 14, lineHeight: 21 },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
  button: {
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1.5,
    borderRadius: 0,
    alignItems: "center",
  },
  avatar: { width: 42, height: 42, borderRadius: 21 },
  search: {
    borderWidth: 2,
    borderRadius: 24,
    height: 48,
    paddingLeft: 16,
    paddingRight: 5,
    paddingVertical: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  searchInput: {
    flex: 1,
    minWidth: 0,
    height: 44,
    minHeight: 44,
    borderWidth: 0,
    backgroundColor: "transparent",
    fontSize: 14,
    padding: 0,
    margin: 0,
  },
  notice: { padding: 14 },
  comment: { paddingVertical: 18, borderBottomWidth: 1, gap: 12 },
  scrim: {
    flex: 1,
    backgroundColor: "#00000088",
    justifyContent: "center",
    padding: 24,
  },
});
