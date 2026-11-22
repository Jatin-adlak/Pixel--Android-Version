const { defineConfig } = require("eslint/config");
const expo = require("eslint-config-expo/flat");

module.exports = defineConfig([
  expo,
  { ignores: ["dist/**", "public/canvaskit.wasm"] },
  // A string on the left of `&&` can become a raw child of a native View.
  {
    files: ["src/app/auth/**/*.tsx"],
    rules: {
      "react/jsx-no-leaked-render": [
        "error",
        { validStrategies: ["coerce", "ternary"] },
      ],
    },
  },
  // These existing native animation files deliberately pass mutable Animated/
  // Reanimated handles to renderers. React Compiler's generic rules cannot model them.
  {
    files: [
      "src/pixel/PixelApp.tsx",
      "src/pixel/BrandIntro.tsx",
      "src/pixel/Notifications.tsx",
      "src/pixel/GlassScene.tsx",
    ],
    rules: { "react-hooks/refs": "off", "react-hooks/immutability": "off" },
  },
]);
