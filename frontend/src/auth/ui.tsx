import { Feather } from "@expo/vector-icons";
import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { palette } from "../pixel/data";

export const authStyles = StyleSheet.create({
  page: { flex: 1, backgroundColor: palette.charcoal },
  content: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 26,
    width: "100%",
    maxWidth: 480,
    alignSelf: "center",
  },
  brand: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginBottom: 40,
  },
  logo: { width: 38, height: 38 },
  wordmark: { color: palette.ivory, fontFamily: "NohemiRegular", fontSize: 30 },
  eyebrow: {
    color: "#93B4FF",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 2,
    marginBottom: 14,
  },
  title: {
    color: palette.ivory,
    fontFamily: "NohemiRegular",
    fontSize: 36,
    lineHeight: 42,
  },
  subtitle: {
    color: "#ADB3BE",
    fontSize: 14,
    lineHeight: 22,
    marginTop: 12,
    marginBottom: 28,
  },
  label: {
    color: palette.ivory,
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 9,
  },
  input: {
    color: palette.ivory,
    backgroundColor: "#252A33",
    borderWidth: 1,
    borderColor: "#505764",
    minHeight: 52,
    paddingHorizontal: 15,
    paddingVertical: 14,
    fontSize: 15,
  },
  field: { marginBottom: 19 },
  buttonShadow: {
    backgroundColor: palette.ivory,
    marginTop: 14,
    marginLeft: 3,
    marginRight: -3,
  },
  button: {
    minHeight: 52,
    backgroundColor: palette.blue,
    borderWidth: 2,
    borderColor: palette.ivory,
    marginLeft: -3,
    marginTop: -3,
    marginBottom: 3,
    marginRight: 3,
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 9,
    padding: 12,
  },
  buttonText: { color: palette.ivory, fontSize: 14, fontWeight: "800" },
  link: {
    color: "#93B4FF",
    fontSize: 13,
    fontWeight: "700",
    paddingVertical: 9,
  },
  muted: { color: "#ADB3BE", fontSize: 12, lineHeight: 19 },
  error: {
    backgroundColor: "#38232B",
    borderLeftWidth: 3,
    borderLeftColor: "#FF8F9F",
    padding: 13,
    marginVertical: 12,
  },
  errorText: { color: "#FFBBC5", fontSize: 13, lineHeight: 20 },
  notice: {
    backgroundColor: "#232D43",
    borderLeftWidth: 3,
    borderLeftColor: palette.blue,
    padding: 14,
    marginVertical: 12,
  },
  noticeText: { color: "#DCE6FF", fontSize: 13, lineHeight: 21 },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
});

export function AuthPage({
  children,
  title,
  subtitle,
  eyebrow = "YOUR CAMPUS. IN FOCUS.",
  dark,
  embedded = false,
  bottomInset = 0,
}: {
  children: ReactNode;
  title: string;
  subtitle: string;
  eyebrow?: string;
  dark?: boolean;
  embedded?: boolean;
  bottomInset?: number;
}) {
  const safe = useSafeAreaInsets();
  const theme =
    dark === undefined ? undefined : dark ? palette.dark : palette.light;
  return (
    <KeyboardAvoidingView
      style={[authStyles.page, theme && { backgroundColor: theme.background }]}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          authStyles.content,
          {
            paddingTop: embedded ? 24 : safe.top + 28,
            paddingBottom: safe.bottom + 30 + bottomInset,
            justifyContent: embedded ? "flex-start" : "center",
          },
        ]}
      >
        {!embedded && (
          <View style={authStyles.brand}>
            <Image
              source={require("../../assets/images/pixel-logo.png")}
              style={authStyles.logo}
            />
            <Text style={[authStyles.wordmark, theme && { color: theme.text }]}>
              Pixel
            </Text>
          </View>
        )}
        <Text
          style={[
            authStyles.eyebrow,
            theme && !dark && { color: palette.blue },
          ]}
        >
          {eyebrow}
        </Text>
        <Text style={[authStyles.title, theme && { color: theme.text }]}>
          {title}
        </Text>
        <Text style={[authStyles.subtitle, theme && { color: theme.muted }]}>
          {subtitle}
        </Text>
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

export function Field({
  label,
  dark,
  ...props
}: TextInputProps & { label: string; dark?: boolean }) {
  const theme =
    dark === undefined ? undefined : dark ? palette.dark : palette.light;
  return (
    <View style={authStyles.field}>
      <Text style={[authStyles.label, theme && { color: theme.text }]}>
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        placeholderTextColor={theme?.muted || "#8C95A5"}
        autoCapitalize="none"
        style={[
          authStyles.input,
          props.multiline && { minHeight: 88 },
          theme && {
            color: theme.text,
            backgroundColor: theme.surface,
            borderColor: theme.line,
          },
        ]}
        {...props}
      />
    </View>
  );
}

export function Action({
  children,
  onPress,
  busy = false,
  disabled = false,
  secondary = false,
}: {
  children: string;
  onPress: () => void;
  busy?: boolean;
  disabled?: boolean;
  secondary?: boolean;
}) {
  return (
    <View
      style={[authStyles.buttonShadow, { opacity: disabled || busy ? 0.5 : 1 }]}
    >
      <Pressable
        accessibilityRole="button"
        disabled={disabled || busy}
        onPress={onPress}
        style={[
          authStyles.button,
          secondary && { backgroundColor: palette.charcoal },
        ]}
      >
        {busy ? (
          <ActivityIndicator color={palette.ivory} />
        ) : (
          <Text style={authStyles.buttonText}>{children}</Text>
        )}
      </Pressable>
    </View>
  );
}

export function Check({
  checked,
  onChange,
  children,
  label,
}: {
  checked: boolean;
  onChange: () => void;
  children: ReactNode;
  label: string;
}) {
  return (
    <View
      style={[authStyles.row, { alignItems: "flex-start", marginVertical: 8 }]}
    >
      <Pressable
        accessibilityRole="checkbox"
        accessibilityLabel={label}
        accessibilityState={{ checked }}
        onPress={onChange}
        style={{ padding: 5, marginLeft: -5 }}
      >
        <View
          style={{
            width: 22,
            height: 22,
            borderWidth: 1.5,
            borderColor: checked ? palette.blue : "#7B8493",
            backgroundColor: checked ? palette.blue : "transparent",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {checked && <Feather name="check" color={palette.ivory} size={16} />}
        </View>
      </Pressable>
      <View style={{ flex: 1, paddingTop: 4 }}>{children}</View>
    </View>
  );
}

export function Message({
  text,
  error = false,
}: {
  text: string;
  error?: boolean;
}) {
  return text ? (
    <View
      accessibilityLiveRegion="polite"
      style={error ? authStyles.error : authStyles.notice}
    >
      <Text style={error ? authStyles.errorText : authStyles.noticeText}>
        {text}
      </Text>
    </View>
  ) : null;
}

export function PolicyModal({
  title,
  text,
  close,
}: {
  title: string;
  text: string;
  close: () => void;
}) {
  return (
    <Modal visible animationType="slide" onRequestClose={close}>
      <AuthPage title={title} subtitle="Read before continuing.">
        <Text style={[authStyles.muted, { fontSize: 14, lineHeight: 24 }]}>
          {text}
        </Text>
        <Action onPress={close}>Continue to PIXEL</Action>
      </AuthPage>
    </Modal>
  );
}
