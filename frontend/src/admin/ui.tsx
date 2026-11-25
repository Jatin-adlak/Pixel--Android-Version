import { createContext, useContext } from "react";
import type { ReactNode } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import DesignedButton from "../pixel/DesignedButton";
import { palette } from "../pixel/data";

export const AdminAppearance = createContext(true);
export const useAdminTheme = () =>
  useContext(AdminAppearance) ? palette.dark : palette.light;
export function Heading({
  children,
  eyebrow,
}: {
  children: ReactNode;
  eyebrow?: string;
}) {
  const t = useAdminTheme();
  return (
    <View style={{ gap: 10 }}>
      {eyebrow && <Text style={u.eyebrow}>{eyebrow}</Text>}
      <Text style={[u.heading, { color: t.text }]}>{children}</Text>
    </View>
  );
}
export function Copy({ children }: { children: ReactNode }) {
  const t = useAdminTheme();
  return <Text style={[u.copy, { color: t.muted }]}>{children}</Text>;
}
export function Panel({ children }: { children: ReactNode }) {
  const t = useAdminTheme();
  return (
    <View
      style={[u.panel, { backgroundColor: t.surface, borderColor: t.line }]}
    >
      {children}
    </View>
  );
}
export function Button({
  children,
  onPress,
  busy = false,
  secondary = false,
  compact = false,
  label,
}: {
  children: ReactNode;
  onPress: () => void;
  busy?: boolean;
  secondary?: boolean;
  danger?: boolean;
  compact?: boolean;
  label?: string;
}) {
  return (
    <DesignedButton
      onPress={onPress}
      disabled={busy}
      selected={!secondary}
      compact={compact}
      label={label}
    >
      {busy ? "Working…" : children}
    </DesignedButton>
  );
}
export function Field({
  label,
  value,
  onChange,
  multiline = false,
  placeholder = "",
  keyboardType = "default",
  secure = false,
  search = false,
}: {
  label: string;
  value: string;
  onChange: (text: string) => void;
  multiline?: boolean;
  placeholder?: string;
  keyboardType?: "default" | "url" | "numeric";
  secure?: boolean;
  search?: boolean;
}) {
  const t = useAdminTheme();
  return (
    <View style={{ gap: 8, flexGrow: 1 }}>
      <Text style={{ color: t.text, fontSize: 13, fontWeight: "700" }}>
        {label}
      </Text>
      <TextInput
        accessibilityLabel={label}
        value={value}
        onChangeText={onChange}
        placeholder={placeholder}
        placeholderTextColor={t.muted}
        multiline={multiline}
        keyboardType={keyboardType}
        inputMode={search ? "search" : undefined}
        autoCapitalize="none"
        secureTextEntry={secure}
        autoCorrect={secure || search ? false : undefined}
        autoComplete={secure ? "new-password" : search ? "off" : undefined}
        maxLength={secure ? 128 : undefined}
        style={[
          u.field,
          {
            color: t.text,
            borderColor: t.line,
            backgroundColor: t.background,
            minHeight: multiline ? 110 : 48,
          },
        ]}
      />
    </View>
  );
}
export function Chip({
  children,
  selected,
  onPress,
  compact = false,
}: {
  children: ReactNode;
  selected?: boolean;
  onPress: () => void;
  compact?: boolean;
}) {
  return (
    <DesignedButton onPress={onPress} selected={selected} compact={compact}>
      {children}
    </DesignedButton>
  );
}
export const u = StyleSheet.create({
  heading: {
    fontFamily: "NohemiRegular",
    fontSize: 30,
    lineHeight: 36,
    letterSpacing: -0.7,
  },
  eyebrow: {
    color: palette.blue,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  copy: { fontSize: 13, lineHeight: 21 },
  panel: { borderWidth: 1, padding: 22, gap: 18, borderRadius: 22 },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    gap: 12,
  },
  buttonBack: { marginTop: 3, marginLeft: 3 },
  buttonFace: {
    borderWidth: 2,
    paddingVertical: 13,
    paddingHorizontal: 18,
    alignItems: "center",
    minHeight: 46,
  },
  field: { borderWidth: 1.5, borderRadius: 12, padding: 14, fontSize: 14 },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderWidth: 1,
    borderRadius: 24,
  },
  label: { fontSize: 16, fontWeight: "700" },
});
