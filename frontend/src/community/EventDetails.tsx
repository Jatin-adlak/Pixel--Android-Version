import { Feather } from "@expo/vector-icons";
import { Linking, Text, View } from "react-native";
import LoadingImage from "../pixel/loading/LoadingImage";
import DesignedButton from "../pixel/DesignedButton";
import { palette } from "../pixel/data";
import type { CampusEvent } from "./types";

export default function EventDetails({
  event,
  dark,
  spotlight,
}: {
  event: CampusEvent;
  dark: boolean;
  spotlight: boolean;
}) {
  const theme = dark ? palette.dark : palette.light;
  const start = new Date(event.starts_at);
  const end = new Date(event.ends_at);
  const validDates =
    !Number.isNaN(start.getTime()) && !Number.isNaN(end.getTime());
  const sameDay = validDates && start.toDateString() === end.toDateString();
  const date = (value: Date) =>
    value.toLocaleDateString(undefined, {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  const time = (value: Date) =>
    value.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
  const detail = (
    icon: "calendar" | "clock" | "map-pin",
    label: string,
    value: string,
  ) => (
    <View style={{ flexDirection: "row", gap: 14, alignItems: "center" }}>
      <View
        style={{
          width: 42,
          height: 42,
          borderRadius: 14,
          backgroundColor: theme.surface,
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Feather name={icon} size={19} color={palette.blue} />
      </View>
      <View style={{ flex: 1, gap: 4 }}>
        <Text style={{ color: theme.muted, fontSize: 11 }}>{label}</Text>
        <Text
          style={{
            color: theme.text,
            fontSize: 14,
            lineHeight: 21,
            fontWeight: "600",
          }}
        >
          {value}
        </Text>
      </View>
    </View>
  );
  return (
    <View style={{ gap: 22 }}>
      {spotlight && !!event.cover_url && (
        <View
          style={{ backgroundColor: palette.blue, marginLeft: 4, marginTop: 4 }}
        >
          <LoadingImage
            dark={dark}
            source={{ uri: event.cover_url }}
            resizeMode="cover"
            accessibilityLabel={`${event.title} cover`}
            style={{
              width: "100%",
              aspectRatio: 1.65,
              borderWidth: 3,
              borderColor: palette.charcoal,
              transform: [{ translateX: -4 }, { translateY: -4 }],
            }}
          />
        </View>
      )}
      <View style={{ gap: 10 }}>
        {!!event.tag && (
          <Text
            style={{
              color: palette.blue,
              fontSize: 11,
              fontWeight: "700",
              letterSpacing: 1.2,
            }}
          >
            {event.tag.toUpperCase()}
          </Text>
        )}
        <Text
          accessibilityRole="header"
          style={{
            color: theme.text,
            fontSize: 24,
            lineHeight: 30,
            fontWeight: "700",
          }}
        >
          {event.title}
        </Text>
      </View>
      <View style={{ gap: 18 }}>
        {validDates &&
          detail(
            "calendar",
            sameDay ? "Date" : "Dates",
            sameDay ? date(start) : `${date(start)} – ${date(end)}`,
          )}
        {validDates &&
          detail(
            "clock",
            sameDay ? "Time" : "Starts / ends",
            sameDay
              ? `${time(start)} – ${time(end)}`
              : `${date(start)}, ${time(start)}\n${date(end)}, ${time(end)}`,
          )}
        {!!event.venue && detail("map-pin", "Venue", event.venue)}
      </View>
      {!!event.description && (
        <View style={{ gap: 9, paddingTop: 4 }}>
          <Text style={{ color: theme.text, fontSize: 16, fontWeight: "700" }}>
            About the event
          </Text>
          <Text style={{ color: theme.muted, fontSize: 14, lineHeight: 23 }}>
            {event.description}
          </Text>
        </View>
      )}
      {!!event.form_url && (
        <View style={{ alignSelf: "flex-start", paddingTop: 2 }}>
          <DesignedButton
            label="Open event form"
            onPress={() => void Linking.openURL(event.form_url)}
          >
            Open event form ↗
          </DesignedButton>
        </View>
      )}
    </View>
  );
}
