import Modal from "../pixel/AppModal";
import { Feather } from "@expo/vector-icons";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Image, PanResponder, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import BackNavigation from "../pixel/BackNavigation";
import PageHeader from "../pixel/PageHeader";
import { PixelMotionLoader } from "../pixel/loading/Loading";
import LiquidPage from "../pixel/LiquidPage";
import DesignedButton from "../pixel/DesignedButton";
import { palette } from "../pixel/data";
import type { Publication } from "./types";

export default function PhotoViewer({
  photo,
  initialImage = 0,
  dark,
  busy,
  position,
  total,
  previous,
  next,
  canPrevious,
  canNext,
  save,
  download,
  close,
}: {
  photo: Publication;
  initialImage?: number;
  dark: boolean;
  busy: boolean;
  position: number;
  total: number;
  previous: () => void;
  next: () => void;
  canPrevious: boolean;
  canNext: boolean;
  save: () => void;
  download: (image?: number) => void;
  close: () => void;
}) {
  const safe = useSafeAreaInsets();
  const theme = dark ? palette.dark : palette.light;
  const [ready, setReady] = useState("");
  const [failed, setFailed] = useState("");
  const [imageIndex, setImageIndex] = useState(initialImage);
  const [frame, setFrame] = useState({ width: 1, height: 1 });
  const [dimensions, setDimensions] = useState({
    key: "",
    width: 1,
    height: 1,
  });
  const images = photo.kind === "post" ? photo.images || [] : [];
  const album = images.length > 0;
  const activeImage = images[imageIndex];
  const imageKey = `${photo.id}:${album ? imageIndex : 0}`;
  const knownWidth = activeImage?.width || photo.image_width;
  const knownHeight = activeImage?.height || photo.image_height;
  const ratio =
    dimensions.key === imageKey
      ? dimensions.width / dimensions.height
      : knownWidth && knownHeight
        ? knownWidth / knownHeight
        : 1;
  const fittedWidth = Math.min(frame.width, frame.height * ratio);
  const fittedHeight = fittedWidth / ratio;
  const coverUrl = activeImage?.cover_url || photo.cover_url;
  const previewUrl = activeImage?.preview_url || photo.preview_url;
  // Some native load events omit source dimensions. Resolve them separately
  // rather than depending on the event payload to size the photo.
  useEffect(() => {
    let active = true;
    if (!previewUrl || (knownWidth && knownHeight)) return;
    Image.getSize(
      previewUrl,
      (width, height) => {
        if (active && width > 0 && height > 0)
          setDimensions({ key: imageKey, width, height });
      },
      () => {},
    );
    return () => {
      active = false;
    };
  }, [imageKey, previewUrl, knownWidth, knownHeight]);
  const navigation = photo.kind === "photo" || images.length > 1;
  const hasPrevious = album ? imageIndex > 0 : canPrevious;
  const hasNext = album ? imageIndex < images.length - 1 : canNext;
  const goPrevious = () => {
    if (album) setImageIndex((i) => Math.max(0, i - 1));
    else previous();
  };
  const goNext = () => {
    if (album) setImageIndex((i) => Math.min(images.length - 1, i + 1));
    else next();
  };
  const current = useRef({
    navigation,
    busy,
    hasNext,
    hasPrevious,
    goNext,
    goPrevious,
  });
  useLayoutEffect(() => {
    current.current = {
      navigation,
      busy,
      hasNext,
      hasPrevious,
      goNext,
      goPrevious,
    };
  });
  // Keep a gesture alive across renders, while using the latest photo/callbacks.
  // PanResponder stores these callbacks; it does not execute them in render.
  // eslint-disable-next-line react-hooks/refs
  const [pan] = useState(() =>
    PanResponder.create({
      onMoveShouldSetPanResponder: (_, gesture) =>
        current.current.navigation &&
        gesture.numberActiveTouches === 1 &&
        Math.abs(gesture.dx) > 16 &&
        Math.abs(gesture.dx) > Math.abs(gesture.dy) * 1.4,
      onPanResponderRelease: (_, gesture) => {
        const state = current.current;
        if (state.busy) return;
        if (
          (gesture.dx < -40 || (gesture.dx < -16 && gesture.vx < -0.5)) &&
          state.hasNext
        )
          state.goNext();
        else if (
          (gesture.dx > 40 || (gesture.dx > 16 && gesture.vx > 0.5)) &&
          state.hasPrevious
        )
          state.goPrevious();
      },
      onPanResponderTerminationRequest: () => false,
    }),
  );
  const arrow = (
    direction: "left" | "right",
    enabled: boolean,
    action: () => void,
  ) => (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={
        direction === "left" ? "Previous photo" : "Next photo"
      }
      disabled={!enabled || busy}
      onPress={action}
      style={{
        width: 34,
        minHeight: 48,
        alignItems: "center",
        justifyContent: "center",
        opacity: enabled && !busy ? 1 : 0.3,
      }}
    >
      <Feather
        name={direction === "left" ? "chevron-left" : "chevron-right"}
        size={24}
        color={theme.text}
      />
    </Pressable>
  );
  return (
    <Modal visible animationType="none" onRequestClose={close}>
      <LiquidPage
        closeDock={close}
        style={{ flex: 1, backgroundColor: theme.background }}
      >
        <PageHeader dark={dark} />
        <View
          style={{
            flex: 1,
            width: "100%",
            maxWidth: 600,
            alignSelf: "center",
            paddingHorizontal: 16,
            paddingTop: 8,
            paddingBottom: safe.bottom + 112,
          }}
        >
          <View
            style={{
              flexDirection: "row",
              alignItems: "center",
              gap: 14,
              height: 56,
            }}
          >
            <BackNavigation onPress={close} />
            <Text
              numberOfLines={1}
              style={{
                flex: 1,
                color: theme.text,
                fontSize: 14,
                fontWeight: "600",
              }}
            >
              {photo.title}
            </Text>
            {navigation && (
              <Text style={{ color: theme.muted, fontSize: 11 }}>
                {album ? imageIndex + 1 : position + 1} /{" "}
                {album ? images.length : total}
              </Text>
            )}
          </View>
          <View
            {...pan.panHandlers}
            onLayout={(event) => setFrame(event.nativeEvent.layout)}
            style={{ flex: 1, justifyContent: "center", alignItems: "center" }}
          >
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Close photo"
              onPress={close}
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: 0,
                right: 0,
              }}
            />
            <Pressable
              accessibilityLabel={photo.title}
              onPress={() => {}}
              style={{ width: fittedWidth, height: fittedHeight }}
            >
              <Image
                pointerEvents="none"
                source={{ uri: coverUrl }}
                style={{ position: "absolute", width: "100%", height: "100%" }}
                resizeMode="contain"
                onLoad={(event) => {
                  if (ready !== imageKey) {
                    const { width, height } = event.nativeEvent?.source ?? {};
                    if (width && height)
                      setDimensions({ key: imageKey, width, height });
                  }
                }}
              />
              <Image
                key={imageKey}
                pointerEvents="none"
                accessibilityLabel={photo.title}
                source={{ uri: previewUrl }}
                style={{ flex: 1 }}
                resizeMode="contain"
                onLoad={(event) => {
                  setReady(imageKey);
                  const { width, height } = event.nativeEvent?.source ?? {};
                  if (width && height)
                    setDimensions({ key: imageKey, width, height });
                }}
                onError={() => setFailed(imageKey)}
              />
              {ready !== imageKey && failed !== imageKey && (
                <PixelMotionLoader dark={dark} overlay />
              )}
            </Pressable>
            {failed === imageKey && (
              <Text
                style={{
                  color: theme.muted,
                  fontSize: 12,
                  textAlign: "center",
                  padding: 12,
                }}
              >
                The preview is unavailable. You can still download the original.
              </Text>
            )}
          </View>
          <View
            style={{
              minHeight: 68,
              flexDirection: "row",
              alignItems: "center",
              gap: 8,
              paddingHorizontal: 8,
              paddingVertical: 8,
              borderWidth: 1.5,
              borderColor: theme.text,
              borderRadius: 30,
              backgroundColor: theme.surface,
            }}
          >
            {navigation && arrow("left", hasPrevious, goPrevious)}
            <View style={{ flex: 1 }}>
              <DesignedButton
                onPress={save}
                disabled={busy}
                selected={photo.saved}
                label={photo.saved ? "Unsave picture" : "Save picture"}
              >
                {photo.saved ? "Saved" : "Save"}
              </DesignedButton>
            </View>
            <View style={{ flex: 1 }}>
              <DesignedButton
                onPress={() => download(album ? imageIndex : undefined)}
                disabled={busy}
                label="Download original quality"
              >
                Download
              </DesignedButton>
            </View>
            {navigation && arrow("right", hasNext, goNext)}
          </View>
        </View>
      </LiquidPage>
    </Modal>
  );
}
