import { Feather } from "@expo/vector-icons";
import { Text, View } from "react-native";
import { palette } from "../pixel/data";

export default function PrivatePictures({ dark }: { dark: boolean }) {
  const theme = dark ? palette.dark : palette.light;
  return (
    <View
      style={{
        minHeight: 210,
        backgroundColor: theme.surface,
        overflow: "hidden",
        borderRadius: 24,
      }}
    >
      <View
        style={{
          flex: 1,
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
          gap: 14,
        }}
      >
        <Feather name="lock" size={26} color={palette.blue} />
        <Text style={{ color: theme.text, fontSize: 20, fontWeight: "700" }}>
          A closer connection
        </Text>
        <Text
          style={{
            color: theme.muted,
            fontSize: 14,
            lineHeight: 21,
            textAlign: "center",
          }}
        >
          Follow this person and wait for acceptance to see their saved
          pictures.
        </Text>
      </View>
    </View>
  );
}
