import { useContext, useState } from "react";
import { Switch, View } from "react-native";
import { api } from "../auth/api";
import LoadingImage from "../pixel/loading/LoadingImage";
import { appendMedia, chooseMedia } from "./media";
import type { AdminEvent, AdminPublication, MediaAsset } from "./types";
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

export default function PublicationEditor({
  initial,
  kind,
  events,
  busy,
  run,
  done,
}: {
  initial?: AdminPublication;
  kind: string;
  events: AdminEvent[];
  busy: boolean;
  run: (fn: () => Promise<void>) => void;
  done: () => void;
}) {
  const dark = useContext(AdminAppearance);
  const [title, setTitle] = useState(initial?.title || "");
  const [caption, setCaption] = useState(initial?.caption || "");
  const [tag, setTag] = useState(initial?.tag || "Cultural");
  const [event, setEvent] = useState(initial?.event || "");
  const [published, setPublished] = useState(initial?.published || false);
  const [original, setOriginal] = useState<MediaAsset | null>(null);
  const [photos, setPhotos] = useState<MediaAsset[]>([]);
  const [cover, setCover] = useState<MediaAsset | null>(null);
  const actualKind = initial?.kind || kind;
  const save = () =>
    run(async () => {
      if (!title.trim() || !event)
        throw new Error("Add a title and choose the event.");
      if (
        !original &&
        !photos.length &&
        !initial?.drive_file_id &&
        !initial?.original_url
      )
        throw new Error("Choose the original image or video.");
      if (
        photos.reduce(
          (sum, photo) => sum + (photo.fileSize || photo.file?.size || 0),
          0,
        ) >
        100 * 1024 * 1024
      )
        throw new Error("Keep the complete post below 100 MB.");
      const body = new FormData();
      Object.entries({
        title,
        caption,
        tag,
        event,
        kind: actualKind,
        published: String(published),
      }).forEach(([k, v]) => body.append(k, v));
      if (original) appendMedia(body, "original_upload", original);
      photos.forEach((file) => appendMedia(body, "original_uploads", file));
      if (cover) appendMedia(body, "cover_upload", cover);
      await api(`/management/publications/${initial ? `${initial.id}/` : ""}`, {
        method: initial ? "PATCH" : "POST",
        body,
        timeoutMs: 600000,
      });
      done();
    });
  return (
    <>
      <Heading
        eyebrow={actualKind === "moment" ? "MOMENTS STUDIO" : "FEED STUDIO"}
      >
        {initial
          ? "Refine the story."
          : actualKind === "moment"
            ? "A moment worth replaying."
            : "Share a new perspective."}
      </Heading>
      <Copy>
        Original media goes to Drive. Likes, comments and saves stay connected
        to this publication.
      </Copy>
      <Panel>
        <Field label="Title" value={title} onChange={setTitle} />
        <Field
          label="Caption"
          value={caption}
          onChange={setCaption}
          multiline
        />
        <Copy>Choose an event</Copy>
        <View style={u.row}>
          {events.map((e) => (
            <Chip
              key={e.id}
              selected={event === e.id}
              onPress={() => {
                setEvent(e.id);
                setTag(e.tag);
              }}
            >
              {e.title}
            </Chip>
          ))}
        </View>
        {!events.length && (
          <Copy>Create an event first, then return to publish its story.</Copy>
        )}
        <Field label="Category / tag" value={tag} onChange={setTag} />
      </Panel>
      <Panel>
        <Heading eyebrow="ORIGINAL MEDIA">
          {actualKind === "moment" ? "Pick your video." : "Pick your frame."}
        </Heading>
        {original && (
          <Copy>
            {original.fileName || "Original selected"} ·{" "}
            {Math.round((original.fileSize || 0) / 1024 / 1024)} MB
          </Copy>
        )}
        {actualKind === "post" && (
          <>
            <Copy>
              {photos.length
                ? `${photos.length} / 10 photos selected`
                : initial?.images?.length
                  ? `${initial.images.length} photos in this post. Choose photos to replace the set.`
                  : "Select 1–10 photos. Their order below is their order in the feed."}
            </Copy>
            {photos.map((file, index) => (
              <View
                key={`${file.uri}-${index}`}
                style={{ flexDirection: "row", alignItems: "center", gap: 10 }}
              >
                <LoadingImage
                  dark={dark}
                  source={{ uri: file.uri }}
                  style={{ width: 54, height: 54, borderRadius: 8 }}
                />
                <View style={{ flex: 1 }}>
                  <Copy>
                    {index + 1}. {file.fileName || "Photo"}
                  </Copy>
                </View>
                {index > 0 && (
                  <Button
                    secondary
                    compact
                    label="Move photo earlier"
                    onPress={() =>
                      setPhotos((old) => {
                        const next = [...old];
                        [next[index - 1], next[index]] = [
                          next[index],
                          next[index - 1],
                        ];
                        return next;
                      })
                    }
                  >
                    ↑
                  </Button>
                )}
                <Button
                  secondary
                  compact
                  label="Remove selected photo"
                  onPress={() =>
                    setPhotos((old) => old.filter((_, i) => i !== index))
                  }
                >
                  ×
                </Button>
              </View>
            ))}
          </>
        )}
        <Button
          secondary
          onPress={() =>
            run(async () => {
              const files = await chooseMedia(
                actualKind === "moment",
                actualKind === "post",
                10,
              );
              if (actualKind === "post" && files.length) {
                if (files.length > 10)
                  throw new Error("Choose at most 10 photos.");
                setPhotos(files);
                setOriginal(null);
              } else if (files[0]) setOriginal(files[0]);
            })
          }
        >
          {actualKind === "moment"
            ? "Choose MP4 video"
            : "Choose up to 10 photos"}
        </Button>
        <Copy>JPEG, PNG or WebP images. MP4 videos. Maximum 100 MB.</Copy>
      </Panel>
      <Panel>
        <Heading eyebrow="COVER PHOTO">Give it a first impression.</Heading>
        {(cover?.uri ||
          initial?.cover_preview_url ||
          initial?.cover_url ||
          (original?.type === "image" ? original.uri : "")) && (
          <LoadingImage
            dark={dark}
            source={{
              uri:
                cover?.uri ||
                initial?.cover_preview_url ||
                initial?.cover_url ||
                original?.uri,
            }}
            style={{ width: "100%", height: 240, borderRadius: 14 }}
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
        <Copy>
          A custom cover appears while a moment loads. If omitted, Drive
          supplies a thumbnail when it is ready.
        </Copy>
      </Panel>
      <Panel>
        <View style={u.row}>
          <Switch value={published} onValueChange={setPublished} />
          <Copy>Publish to campus</Copy>
        </View>
        <Button busy={busy} onPress={save}>
          {published ? "Save & publish" : "Save draft"}
        </Button>
      </Panel>
    </>
  );
}
