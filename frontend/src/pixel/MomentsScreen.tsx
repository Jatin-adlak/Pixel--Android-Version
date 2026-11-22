import { Feather } from "@expo/vector-icons";
import { useVideoPlayer, VideoView } from "expo-video";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  FlatList,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { palette } from "./data";
import { PixelMotionLoader } from "./loading/Loading";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useMomentAudio } from "./MomentAudio";

export type MomentClip = {
  id: string;
  video_url: string;
  title: string;
  caption: string;
  cover_url?: string;
};

function Clip({
  item,
  active,
  height,
  actions,
  overlayBottom,
}: {
  item: MomentClip;
  active: boolean;
  height: number;
  actions?: ReactNode;
  overlayBottom: number;
}) {
  const { muted, toggle } = useMomentAudio();
  const [hasRenderedFrame, setHasRenderedFrame] = useState(false);
  const player = useVideoPlayer(item.video_url, (video) => {
    video.loop = true;
    video.muted = muted;
    video.bufferOptions = { preferredForwardBufferDuration: 10 };
  });
  useEffect(() => {
    if (active) player.play();
    else player.pause();
  }, [active, player]);
  // Expo Video's native handle exposes writable player properties.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/immutability -- Writable Expo Video native property.
    player.muted = muted;
  }, [muted, player]);
  return (
    <View style={{ height, backgroundColor: "#000", overflow: "hidden" }}>
      <VideoView
        player={player}
        style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
        contentFit="contain"
        surfaceType="textureView"
        nativeControls={false}
        onFirstFrameRender={() => setHasRenderedFrame(true)}
      />
      {/* Buffering must never bring the initial cover back over the video. */}
      {!hasRenderedFrame && !!item.cover_url && (
        <Image
          source={{ uri: item.cover_url }}
          style={[StyleSheet.absoluteFill, { width: "100%", height: "100%" }]}
          resizeMode="contain"
        />
      )}
      {!hasRenderedFrame && active && <PixelMotionLoader dark overlay />}
      <View style={[styles.caption, { bottom: overlayBottom }]}>
        <Text numberOfLines={2} style={styles.clipTitle}>
          {item.title}
        </Text>
        {!!item.caption && (
          <Text numberOfLines={2} style={styles.clipBody}>
            {item.caption}
          </Text>
        )}
      </View>
      <View
        style={{ position: "absolute", right: 10, bottom: overlayBottom + 58 }}
      >
        {actions}
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={muted ? "Unmute video" : "Mute video"}
        onPress={toggle}
        style={[styles.sound, { bottom: overlayBottom }]}
      >
        <Feather
          name={muted ? "volume-x" : "volume-2"}
          size={22}
          color={palette.ivory}
        />
      </Pressable>
    </View>
  );
}

// Video-only feed: no sample photos or unrelated remote videos stand in for content.
export default function MomentsScreen({
  clips,
  height,
  renderActions,
}: {
  clips: MomentClip[];
  height: number;
  renderActions?: (item: MomentClip) => ReactNode;
}) {
  const safe = useSafeAreaInsets();
  const [active, setActive] = useState<string | null>(clips[0]?.id || null);
  const [onViewable] = useState(
    () =>
      ({ viewableItems }: { viewableItems: { item: MomentClip }[] }) => {
        setActive(viewableItems[0]?.item.id || null);
      },
  );
  if (!clips.length)
    return (
      <View style={[styles.empty, { height }]}>
        <Feather name="play-circle" color={palette.blue} size={48} />
        <Text style={styles.title}>A moment worth replaying</Text>
        <Text
          style={[styles.body, { textAlign: "center", paddingHorizontal: 35 }]}
        >
          Short campus videos will fill this space. The club’s first drop is on
          its way.
        </Text>
      </View>
    );
  return (
    <FlatList
      data={clips}
      keyExtractor={(item) => item.id}
      pagingEnabled
      snapToInterval={height}
      decelerationRate="fast"
      showsVerticalScrollIndicator={false}
      getItemLayout={(_, index) => ({
        length: height,
        offset: height * index,
        index,
      })}
      renderItem={({ item }) => (
        <Clip
          item={item}
          height={height}
          active={item.id === (active || clips[0]?.id)}
          actions={renderActions?.(item)}
          overlayBottom={Math.max(safe.bottom, 12) + 110}
        />
      )}
      onViewableItemsChanged={onViewable}
      viewabilityConfig={{ itemVisiblePercentThreshold: 80 }}
      windowSize={3}
      initialNumToRender={1}
      maxToRenderPerBatch={2}
    />
  );
}
const styles = StyleSheet.create({
  empty: {
    alignItems: "center",
    justifyContent: "center",
    gap: 15,
    backgroundColor: "#000",
  },
  caption: {
    position: "absolute",
    bottom: 16,
    left: 12,
    right: 70,
    backgroundColor: "#00000055",
    borderRadius: 12,
    padding: 10,
    gap: 6,
  },
  clipTitle: {
    color: palette.ivory,
    fontSize: 16,
    lineHeight: 21,
    fontFamily: "NohemiRegular",
  },
  clipBody: { color: "#E1E4E9", fontSize: 12, lineHeight: 17 },
  title: {
    color: palette.ivory,
    fontSize: 24,
    fontFamily: "NohemiRegular",
    marginTop: 12,
  },
  body: { color: "#C8CED8", fontSize: 13, lineHeight: 21, marginTop: 10 },
  sound: {
    position: "absolute",
    bottom: 16,
    right: 10,
    padding: 10,
    backgroundColor: "#181A1D99",
    borderRadius: 30,
  },
});
