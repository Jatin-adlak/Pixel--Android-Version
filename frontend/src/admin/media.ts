import * as ImagePicker from "expo-image-picker";
import { Platform } from "react-native";
export async function chooseMedia(video = false, multiple = false, limit = 20) {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: video ? ["videos"] : ["images"],
    allowsMultipleSelection: multiple,
    selectionLimit: multiple ? limit : 1,
    quality: 1,
  });
  return result.canceled ? [] : result.assets;
}
export function appendMedia(
  body: FormData,
  key: string,
  asset: ImagePicker.ImagePickerAsset,
) {
  if (Platform.OS === "web" && asset.file) body.append(key, asset.file);
  else
    body.append(key, {
      uri: asset.uri,
      name:
        asset.fileName || (asset.type === "video" ? "moment.mp4" : "photo.jpg"),
      type:
        asset.mimeType || (asset.type === "video" ? "video/mp4" : "image/jpeg"),
    } as unknown as Blob);
}
