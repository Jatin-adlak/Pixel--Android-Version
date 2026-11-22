import Modal from "../pixel/AppModal";
import { Feather } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useEffect, useRef, useState } from "react";
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  Text,
  View,
} from "react-native";
import { api, ApiError } from "../auth/api";
import DesignedButton from "../pixel/DesignedButton";
import { palette } from "../pixel/data";

type Job = {
  id: string;
  status: string;
  phase: string;
  processed: number;
  total: number;
  skipped: number;
  match_count: number;
  error: string;
};
const CONSENT = "face-event-search-v1";

export default function FaceSearchControl({
  eventId,
  dark,
  onResults,
}: {
  eventId: string;
  dark: boolean;
  onResults: (path: string | null) => void;
}) {
  const theme = dark ? palette.dark : palette.light;
  const [job, setJob] = useState<Job | null>(null);
  const [uploading, setUploading] = useState(false);
  const [prompt, setPrompt] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [filtered, setFiltered] = useState(false);
  const jobId = useRef<string | null>(null);
  const uploadController = useRef<AbortController | null>(null);
  const onResultsRef = useRef(onResults);
  const mounted = useRef(true);
  const [pulse] = useState(() => new Animated.Value(0));
  const [trackWidth, setTrackWidth] = useState(250);
  const processing =
    uploading || job?.status === "queued" || job?.status === "processing";
  useEffect(() => {
    onResultsRef.current = onResults;
  }, [onResults]);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      uploadController.current?.abort();
      if (jobId.current)
        void api(`/face-search/${jobId.current}/`, { method: "DELETE" }).catch(
          () => {},
        );
    };
  }, []);
  useEffect(() => {
    if (!processing) return;
    const animation = Animated.loop(
      Animated.timing(pulse, {
        toValue: 1,
        duration: 1500,
        easing: Easing.linear,
        useNativeDriver: Platform.OS !== "web",
      }),
    );
    animation.start();
    return () => {
      animation.stop();
      pulse.setValue(0);
    };
  }, [processing, pulse]);
  useEffect(() => {
    if (!job || !["queued", "processing"].includes(job.status)) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const result = await api<Job>(`/face-search/${job.id}/`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setError("");
        setJob(result);
        if (result.status === "complete") {
          setFiltered(true);
          onResultsRef.current(`/face-search/${result.id}/results/`);
        } else if (["failed", "expired", "cancelled"].includes(result.status)) {
          setError(
            result.error ||
              "This search ended. Please choose your photo again.",
          );
        } else timer = setTimeout(poll, 1200);
      } catch (e) {
        if (!controller.signal.aborted) {
          if (e instanceof ApiError && [403, 404, 410].includes(e.status)) {
            setJob((old) => (old ? { ...old, status: "failed" } : null));
            setError("This event or search is no longer available.");
            return;
          }
          setError(
            e instanceof Error
              ? e.message
              : "Could not check matching progress.",
          );
          timer = setTimeout(poll, 3000);
        }
      }
    };
    timer = setTimeout(poll, 500);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
    // Each job ID owns one polling loop; progress updates must not restart it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.id]);
  const choosePhoto = async () => {
    setPrompt(false);
    setError("");
    try {
      const choice = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsMultipleSelection: false,
        quality: 1,
      });
      if (choice.canceled || !choice.assets[0]) return;
      const asset = choice.assets[0];
      if ((asset.fileSize ?? asset.file?.size ?? 0) > 5 * 1024 * 1024) {
        setError("Choose a clear photo up to 5 MB.");
        return;
      }
      setUploading(true);
      const controller = new AbortController();
      uploadController.current = controller;
      const body = new FormData();
      body.append("consent", CONSENT);
      if (Platform.OS === "web" && asset.file) body.append("photo", asset.file);
      else
        body.append("photo", {
          uri: asset.uri,
          name: `my-photo.${asset.mimeType === "image/png" ? "png" : asset.mimeType === "image/webp" ? "webp" : "jpg"}`,
          type: asset.mimeType || "image/jpeg",
        } as unknown as Blob);
      if (jobId.current)
        await api(`/face-search/${jobId.current}/`, { method: "DELETE" });
      const result = await api<Job>(`/events/${eventId}/face-search/`, {
        method: "POST",
        body,
        timeoutMs: 90000,
        signal: controller.signal,
      });
      if (!mounted.current) {
        void api(`/face-search/${result.id}/`, { method: "DELETE" }).catch(
          () => {},
        );
        return;
      }
      jobId.current = result.id;
      setJob(result);
    } catch (e) {
      if (mounted.current && !uploadController.current?.signal.aborted)
        setError(
          e instanceof Error ? e.message : "Could not upload your photo.",
        );
    } finally {
      uploadController.current = null;
      if (mounted.current) setUploading(false);
    }
  };
  const begin = async () => {
    setChecking(true);
    setError("");
    try {
      const state = await api<{ available: boolean; active_job: Job | null }>(
        `/events/${eventId}/face-search/`,
        { timeoutMs: 30000 },
      );
      if (!mounted.current) return;
      if (state.active_job) {
        jobId.current = state.active_job.id;
        setJob(state.active_job);
        return;
      }
      if (!state.available) {
        setError(
          "Face matching is temporarily unavailable. Please try again shortly.",
        );
        return;
      }
      setPrompt(true);
    } catch (e) {
      if (mounted.current)
        setError(
          e instanceof Error ? e.message : "Could not prepare your search.",
        );
    } finally {
      if (mounted.current) setChecking(false);
    }
  };
  const cancel = async () => {
    uploadController.current?.abort();
    if (uploading) {
      setUploading(false);
      setError(
        "Upload stopped. If it already reached PIXEL, tap Find yourself to resume or cancel the search.",
      );
    }
    if (!jobId.current) return;
    try {
      await api(`/face-search/${jobId.current}/`, { method: "DELETE" });
      jobId.current = null;
      setJob(null);
      setError("");
      setFiltered(false);
      onResultsRef.current(null);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not cancel. Please try again.",
      );
    }
  };
  const progress = job?.total
    ? Math.min(100, Math.round((job.processed / job.total) * 100))
    : 0;
  return (
    <View style={{ gap: 12 }}>
      {processing ? (
        <View
          accessibilityRole="progressbar"
          accessibilityLabel={uploading ? "Uploading your photo" : job?.phase}
          accessibilityValue={{ min: 0, max: 100, now: progress }}
          style={{
            padding: 16,
            borderRadius: 18,
            backgroundColor: theme.surface,
            gap: 12,
          }}
        >
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
            <Feather name="search" size={18} color={palette.blue} />
            <Text
              style={{
                flex: 1,
                color: theme.text,
                fontSize: 13,
                fontWeight: "600",
              }}
            >
              {uploading
                ? "Uploading your photo…"
                : job?.phase || "Preparing your search…"}
            </Text>
            {
              <Pressable
                accessibilityRole="button"
                onPress={() => void cancel()}
                hitSlop={8}
              >
                <Text style={{ color: theme.muted, fontSize: 12 }}>Cancel</Text>
              </Pressable>
            }
          </View>
          <View
            onLayout={(e) => setTrackWidth(e.nativeEvent.layout.width)}
            style={{
              height: 6,
              borderRadius: 3,
              overflow: "hidden",
              backgroundColor: theme.background,
            }}
          >
            <View
              style={{
                position: "absolute",
                height: "100%",
                width: `${progress}%`,
                backgroundColor: palette.blue,
              }}
            />
            <Animated.View
              style={{
                position: "absolute",
                height: "100%",
                width: "30%",
                backgroundColor: "#92B6FF",
                opacity: 0.7,
                transform: [
                  {
                    translateX: pulse.interpolate({
                      inputRange: [0, 1],
                      outputRange: [-trackWidth * 0.3, trackWidth],
                    }),
                  },
                ],
              }}
            />
          </View>
          <Text style={{ color: theme.muted, fontSize: 12 }}>
            {job?.total
              ? `${job.processed} of ${job.total} photos checked · ${progress}%`
              : "Please keep this event open while we prepare your matches."}
          </Text>
        </View>
      ) : (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
          <View style={{ flex: filtered ? undefined : 1 }}>
            <DesignedButton
              selected
              compact={filtered}
              disabled={checking}
              onPress={() => void begin()}
            >
              {checking
                ? "Preparing face search…"
                : filtered
                  ? "Try another photo"
                  : "Find yourself"}
            </DesignedButton>
          </View>
          {filtered && (
            <Pressable
              accessibilityRole="button"
              onPress={() => {
                setFiltered(false);
                onResultsRef.current(null);
              }}
              style={{ paddingVertical: 10 }}
            >
              <Text
                style={{ color: palette.blue, fontSize: 13, fontWeight: "600" }}
              >
                Show all photos
              </Text>
            </Pressable>
          )}
        </View>
      )}
      {filtered && (
        <Text style={{ color: theme.muted, fontSize: 13, lineHeight: 20 }}>
          {job?.match_count
            ? `${job.match_count} matching photos. Save or download them as usual.`
            : "No confident matches found. Try a sharper, front-facing photo."}
          {job?.skipped
            ? ` ${job.skipped} photos could not be checked; try again later for a complete search.`
            : ""}
        </Text>
      )}
      {!!error && (
        <Text
          accessibilityLiveRegion="polite"
          style={{ color: "#DA6174", fontSize: 13, lineHeight: 20 }}
        >
          {error}
        </Text>
      )}
      <Modal
        visible={prompt}
        transparent
        animationType="fade"
        onRequestClose={() => setPrompt(false)}
      >
        <View
          pointerEvents="box-none"
          style={{
            flex: 1,
            backgroundColor: "#00000099",
            justifyContent: "center",
            alignItems: "center",
            padding: 24,
          }}
        >
          <View
            style={{
              width: "100%",
              maxWidth: 390,
              padding: 24,
              borderRadius: 24,
              backgroundColor: theme.surface,
              gap: 18,
            }}
          >
            <Feather name="user-check" size={28} color={palette.blue} />
            <Text
              style={{ color: theme.text, fontSize: 20, fontWeight: "700" }}
            >
              Find your moments
            </Text>
            <Text style={{ color: theme.muted, fontSize: 14, lineHeight: 22 }}>
              Choose a clear photo of yourself with only your face visible.
              Allow PIXEL to compare it with photos in this event. Your upload
              is deleted after checking and is never added to the gallery.
            </Text>
            <DesignedButton selected onPress={() => void choosePhoto()}>
              Agree & choose my photo
            </DesignedButton>
            <Pressable
              accessibilityRole="button"
              onPress={() => setPrompt(false)}
              style={{ alignSelf: "center", padding: 8 }}
            >
              <Text style={{ color: theme.muted, fontSize: 13 }}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}
