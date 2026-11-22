export type PhotoSize = { width: number; height: number };
export function postFrame(
  availableWidth: number,
  dimensions: (PhotoSize | undefined)[],
) {
  const valid = dimensions.filter(
    (size): size is PhotoSize =>
      !!size &&
      Number.isFinite(size.width) &&
      Number.isFinite(size.height) &&
      size.width > 0 &&
      size.height > 0,
  );
  if (!valid.length) return { height: Math.max(1, availableWidth), scale: 1 };
  const width = Math.max(...valid.map((size) => size.width));
  const height = Math.max(...valid.map((size) => size.height));
  const scale = Math.min(1, Math.max(1, availableWidth) / width);
  return { height: height * scale, scale };
}
