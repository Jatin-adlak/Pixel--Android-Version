import { useContext, useState } from "react";
import { Switch, View } from "react-native";
import { api } from "../auth/api";
import LoadingImage from "../pixel/loading/LoadingImage";
import { appendMedia, chooseMedia } from "./media";
import type { AdminEvent, MediaAsset } from "./types";
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

function dateParts(value?: string, offset = 0) {
  const v = value ? new Date(value) : new Date(Date.now() + offset * 86400000);
  return {
    date: v.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" }),
    time: v.toLocaleTimeString("en-GB", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }),
  };
}
export default function EventEditor({
  initial,
  spotlight,
  run,
  done,
  busy,
}: {
  initial?: AdminEvent;
  spotlight: boolean;
  run: (fn: () => Promise<void>) => void;
  done: () => void;
  busy: boolean;
}) {
  const dark = useContext(AdminAppearance);
  const start = dateParts(initial?.starts_at, spotlight ? 1 : -1),
    end = dateParts(initial?.ends_at, spotlight ? 1 : -1);
  const [title, setTitle] = useState(initial?.title || "");
  const [tag, setTag] = useState(initial?.tag || "Cultural");
  const [description, setDescription] = useState(initial?.description || "");
  const [venue, setVenue] = useState(initial?.venue || "");
  const [startDate, setStartDate] = useState(start.date),
    [startTime, setStartTime] = useState(start.time);
  const [endDate, setEndDate] = useState(end.date),
    [endTime, setEndTime] = useState(end.time);
  const [multiple, setMultiple] = useState(start.date !== end.date);
  const [folder, setFolder] = useState(initial?.drive_folder_id || "");
  const [form, setForm] = useState(initial?.form_url || "");
  const [published, setPublished] = useState(initial?.published || false);
  const [cover, setCover] = useState<MediaAsset | null>(null);
  const save = () =>
    run(async () => {
      if (!title.trim() || !venue.trim() || !description.trim())
        throw new Error("Add the event name, about and venue.");
      const starts = new Date(`${startDate}T${startTime}:00+05:30`),
        ends = new Date(
          `${multiple ? endDate : startDate}T${endTime}:00+05:30`,
        );
      if (isNaN(starts.valueOf()) || isNaN(ends.valueOf()))
        throw new Error("Use dates as YYYY-MM-DD and times as HH:MM.");
      if (ends < starts) throw new Error("The event must end after it starts.");
      if (!spotlight && !folder.trim())
        throw new Error(
          "Connect the existing Drive folder containing this completed event’s photographs.",
        );
      if (!spotlight && ends > new Date())
        throw new Error(
          "Gallery folders are for completed events. Create an announcement in Spotlight for upcoming activities.",
        );
      const body = new FormData();
      const values = {
        title,
        tag,
        description,
        venue,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
        ...(!spotlight
          ? {
              drive_folder_id:
                folder.match(/\/folders\/([\w-]+)/)?.[1] || folder,
            }
          : {}),
        form_url: form,
        published: String(published),
      };
      Object.entries(values).forEach(([k, v]) => body.append(k, v));
      if (cover) appendMedia(body, "cover_upload", cover);
      else if (initial?.cover_drive_file_id)
        body.append("cover_drive_file_id", initial.cover_drive_file_id);
      else if (initial?.cover_url) body.append("cover_url", initial.cover_url);
      await api(
        `/management/${spotlight ? "spotlights" : "events"}/${initial ? `${initial.id}/` : ""}`,
        {
          method: initial ? "PATCH" : "POST",
          body,
          timeoutMs: 180000,
        },
      );
      done();
    });
  return (
    <>
      <Heading eyebrow={spotlight ? "SPOTLIGHT STUDIO" : "GALLERY FOLDER"}>
        {initial
          ? "Keep the details in focus."
          : spotlight
            ? "What’s coming to campus?"
            : "Keep the memories together."}
      </Heading>
      <Copy>
        {spotlight
          ? "Announce an upcoming college activity with dates, venue and registration details."
          : "Connect the Drive folder containing photographs from an event that has already happened."}
      </Copy>
      <Panel>
        <Field
          label={spotlight ? "Announcement title" : "Event folder name"}
          value={title}
          onChange={setTitle}
          placeholder="e.g. Annual Sports Meet"
        />
        <View style={u.row}>
          {["Sports", "Cultural", "Technical"].map((t) => (
            <Chip key={t} selected={tag === t} onPress={() => setTag(t)}>
              {t}
            </Chip>
          ))}
        </View>
        <Field label="Category / tag" value={tag} onChange={setTag} />
        <Field
          label="About the event"
          value={description}
          onChange={setDescription}
          multiline
        />
        <Field label="Venue" value={venue} onChange={setVenue} />
        <View style={u.row}>
          <Copy>Multiple days</Copy>
          <Switch value={multiple} onValueChange={setMultiple} />
        </View>
        <View style={u.row}>
          <Field
            label="Start date · YYYY-MM-DD"
            value={startDate}
            onChange={setStartDate}
          />
          <Field
            label="Start time · HH:MM"
            value={startTime}
            onChange={setStartTime}
          />
        </View>
        <View style={u.row}>
          {multiple && (
            <Field
              label="End date · YYYY-MM-DD"
              value={endDate}
              onChange={setEndDate}
            />
          )}
          <Field
            label="End time · HH:MM"
            value={endTime}
            onChange={setEndTime}
          />
        </View>
        <Copy>All event times are in India Standard Time.</Copy>
      </Panel>
      <Panel>
        <Heading eyebrow="THE FIRST IMPRESSION">Choose a cover.</Heading>
        {(cover?.uri || initial?.cover_preview_url || initial?.cover_url) && (
          <LoadingImage
            dark={dark}
            source={{
              uri:
                cover?.uri || initial?.cover_preview_url || initial?.cover_url,
            }}
            style={{ width: "100%", height: 240, borderRadius: 14 }}
            resizeMode="cover"
          />
        )}
        <Button
          secondary
          onPress={() =>
            run(async () => {
              const files = await chooseMedia();
              if (files[0]) setCover(files[0]);
            })
          }
        >
          Choose cover photo
        </Button>
        {!spotlight && (
          <>
            <Field
              label="Event Drive folder · required"
              value={folder}
              onChange={setFolder}
              placeholder="Paste the Drive folder link containing this event’s photos"
            />
            <Copy>
              This folder supplies the Gallery photographs and stays
              synchronized with PIXEL.
            </Copy>
          </>
        )}
        {spotlight && (
          <Field
            label="Registration form · optional"
            value={form}
            onChange={setForm}
            placeholder="https://forms.gle/…"
            keyboardType="url"
          />
        )}
      </Panel>
      <Panel>
        <View style={u.row}>
          <Switch value={published} onValueChange={setPublished} />
          <Copy>Publish to campus</Copy>
        </View>
        <Copy>
          Drafts stay in this workspace. Published events become visible to
          signed-in members.
        </Copy>
        <Button busy={busy} onPress={save}>
          {published
            ? spotlight
              ? "Publish announcement"
              : "Publish event folder"
            : "Save draft"}
        </Button>
      </Panel>
    </>
  );
}
