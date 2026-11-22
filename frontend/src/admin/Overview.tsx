import { Feather } from "@expo/vector-icons";
import { Pressable, Text, View } from "react-native";
import type { Summary } from "./types";
import { Button, Copy, Panel, u, useAdminTheme } from "./ui";
import { palette } from "../pixel/data";

type Destination =
  | "Gallery"
  | "Posts"
  | "Moments"
  | "Spotlight"
  | "Members"
  | "Comments"
  | "Storage";
export default function Overview({
  summary,
  open,
}: {
  summary: Summary;
  open: (section: Destination) => void;
}) {
  const theme = useAdminTheme();
  const tiles: {
    label: string;
    value: number;
    icon: keyof typeof Feather.glyphMap;
    section: Destination;
  }[] = [
    {
      label: "Event folders",
      value: summary.events,
      icon: "folder",
      section: "Gallery",
    },
    { label: "Posts", value: summary.posts, icon: "image", section: "Posts" },
    {
      label: "Moments",
      value: summary.moments,
      icon: "play",
      section: "Moments",
    },
    {
      label: "Photos",
      value: summary.photos,
      icon: "camera",
      section: "Gallery",
    },
    {
      label: "Members",
      value: summary.members,
      icon: "users",
      section: "Members",
    },
    {
      label: "Comments",
      value: summary.comments,
      icon: "message-circle",
      section: "Comments",
    },
  ];
  const heading = (label: string) => (
    <Text style={[u.label, { color: theme.text }]}>{label}</Text>
  );
  return (
    <View style={{ gap: 22 }}>
      <View style={{ gap: 12 }}>
        {[0, 2, 4].map((start) => (
          <View key={start} style={{ flexDirection: "row", gap: 12 }}>
            {tiles.slice(start, start + 2).map((tile) => (
              <Pressable
                key={tile.label}
                accessibilityRole="button"
                accessibilityLabel={`${tile.label}: ${tile.value}`}
                onPress={() => open(tile.section)}
                style={({ pressed }) => ({
                  flex: 1,
                  minWidth: 0,
                  height: 126,
                  borderRadius: 22,
                  borderWidth: 1,
                  borderColor: theme.line,
                  backgroundColor: theme.surface,
                  padding: 18,
                  justifyContent: "space-between",
                  opacity: pressed ? 0.75 : 1,
                })}
              >
                <View
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Text
                    style={{
                      color: theme.text,
                      fontSize: 30,
                      fontWeight: "700",
                    }}
                  >
                    {tile.value.toLocaleString()}
                  </Text>
                  <Feather name={tile.icon} size={19} color={palette.blue} />
                </View>
                <Text style={{ color: theme.muted, fontSize: 13 }}>
                  {tile.label}
                </Text>
              </Pressable>
            ))}
          </View>
        ))}
      </View>
      <Panel>
        {heading("Publishing at a glance")}
        <View style={{ flexDirection: "row", gap: 12 }}>
          {[
            [summary.published, "Live"],
            [summary.drafts, "Drafts"],
            [summary.upcoming, "Upcoming"],
          ].map(([count, label]) => (
            <View key={label} style={{ flex: 1, gap: 6 }}>
              <Text
                style={{ color: theme.text, fontSize: 24, fontWeight: "700" }}
              >
                {count}
              </Text>
              <Copy>{label}</Copy>
            </View>
          ))}
        </View>
        <Copy>
          Live counts posts and moments ready to view. Upcoming counts published
          Spotlight announcements.
        </Copy>
        {!!summary.unavailable && (
          <Copy>
            {summary.unavailable} published media item(s) need attention.
          </Copy>
        )}
      </Panel>
      <View style={{ flexDirection: "row", gap: 12 }}>
        {[
          [summary.likes, "Likes", "heart"],
          [summary.saves, "Saves", "bookmark"],
        ].map(([count, label, icon]) => (
          <View
            key={label}
            style={{
              flex: 1,
              minWidth: 0,
              height: 126,
              padding: 18,
              justifyContent: "space-between",
              borderRadius: 22,
              backgroundColor: theme.surface,
              borderWidth: 1,
              borderColor: theme.line,
            }}
          >
            <View
              style={{ flexDirection: "row", justifyContent: "space-between" }}
            >
              <Text
                style={{ color: theme.text, fontSize: 30, fontWeight: "700" }}
              >
                {count}
              </Text>
              <Feather
                name={icon as "heart" | "bookmark"}
                color={palette.blue}
                size={18}
              />
            </View>
            <Copy>{label}</Copy>
          </View>
        ))}
      </View>
      <Panel>
        {heading("Create & manage")}
        <Copy>Keep your next campus story moving.</Copy>
        {[
          ["Posts", "Moments"],
          ["Gallery", "Spotlight"],
        ].map((row, index) => (
          <View key={index} style={{ flexDirection: "row", gap: 12 }}>
            {row.map((section) => (
              <View key={section} style={{ flex: 1, minWidth: 0 }}>
                <Button secondary onPress={() => open(section as Destination)}>
                  {section}
                </Button>
              </View>
            ))}
          </View>
        ))}
      </Panel>
      <Panel>
        {heading("Drive & gallery health")}
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <Feather
            name={summary.drive_connected ? "check-circle" : "alert-circle"}
            size={18}
            color={palette.blue}
          />
          <Copy>
            {summary.drive_connected
              ? "Pixel Drive connected"
              : "Drive connection needed"}
          </Copy>
        </View>
        <Copy>
          {summary.sync.errors
            ? `${summary.sync.errors} event folder(s) need a sync check.`
            : "No gallery sync errors reported."}
        </Copy>
        <Copy>
          {summary.sync.last_success_at
            ? `Last successful sync · ${new Date(summary.sync.last_success_at).toLocaleString()}`
            : "No completed gallery sync yet."}
        </Copy>
        <View style={{ alignSelf: "flex-start" }}>
          <Button
            secondary
            onPress={() => open(summary.sync.errors ? "Gallery" : "Storage")}
          >
            {summary.sync.errors ? "Check galleries" : "Manage storage"}
          </Button>
        </View>
      </Panel>
      <Panel>
        {heading("Recent posts & moments")}
        {!summary.recent.length && (
          <Copy>Your new posts and moments will appear here.</Copy>
        )}
        {summary.recent.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityLabel={`Manage ${item.title}`}
            onPress={() => open(item.kind === "moment" ? "Moments" : "Posts")}
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 12,
              minHeight: 58,
            }}
          >
            <Feather
              name={item.kind === "moment" ? "play" : "image"}
              color={palette.blue}
              size={20}
            />
            <View style={{ flex: 1, gap: 5 }}>
              <Text
                numberOfLines={1}
                style={{ color: theme.text, fontSize: 14, fontWeight: "600" }}
              >
                {item.title}
              </Text>
              <Copy>
                {!item.published
                  ? "Draft"
                  : item.available
                    ? "Published"
                    : "Needs attention"}{" "}
                · {new Date(item.created_at).toLocaleDateString()}
              </Copy>
            </View>
            <Feather name="chevron-right" size={18} color={theme.muted} />
          </Pressable>
        ))}
      </Panel>
    </View>
  );
}
