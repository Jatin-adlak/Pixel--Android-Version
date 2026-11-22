import type { ReactNode } from "react";
import { Pressable, Text, View } from "react-native";
import { palette } from "./data";

// The original Gallery filter button: ivory/blue face, charcoal outline,
// and the same three-pixel offset that collapses while pressed.
export default function DesignedButton({
  children,
  onPress,
  selected = false,
  disabled = false,
  label,
  compact = false,
  stretch = false,
}: {
  children: ReactNode;
  onPress: () => void;
  selected?: boolean;
  disabled?: boolean;
  label?: string;
  compact?: boolean;
  stretch?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected, disabled }}
      disabled={disabled}
      hitSlop={compact ? 6 : undefined}
      onPress={onPress}
      style={{
        flex: stretch ? 1 : undefined,
        backgroundColor: selected ? palette.ivory : palette.blue,
        marginTop: 3,
        marginLeft: 3,
        opacity: disabled ? 0.55 : 1,
      }}
    >
      {({ pressed }) => (
        <View
          style={{
            flex: stretch ? 1 : undefined,
            minHeight: compact ? 30 : 44,
            paddingVertical: compact ? 5 : 10,
            paddingHorizontal: compact ? 8 : 12,
            borderWidth: 2,
            borderColor: palette.charcoal,
            backgroundColor: selected ? palette.blue : palette.ivory,
            alignItems: "center",
            justifyContent: "center",
            transform: [
              { translateX: pressed ? 0 : -3 },
              { translateY: pressed ? 0 : -3 },
            ],
          }}
        >
          <Text
            style={{
              color: selected ? palette.ivory : palette.charcoal,
              fontSize: compact ? 11 : 12,
              fontWeight: "700",
            }}
          >
            {children}
          </Text>
        </View>
      )}
    </Pressable>
  );
}
