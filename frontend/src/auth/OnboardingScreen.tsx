import { useEffect, useState } from "react";
import { Image, Platform, Pressable, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { api } from "./api";
import { useAuth } from "./AuthProvider";
import type { CampusUser } from "./types";
import { Action, AuthPage, authStyles as s, Field, Message } from "./ui";
import { Feather } from "@expo/vector-icons";
import { useAppInbox } from "../pixel/AppInboxContext";
import DesignedButton from "../pixel/DesignedButton";
import { palette } from "../pixel/data";

export default function OnboardingScreen({
  onComplete,
  onCancel,
}: { onComplete?: () => void; onCancel?: () => void } = {}) {
  const { user, updateUser, logout } = useAuth();
  const { dark } = useAppInbox();
  const theme = dark ? palette.dark : palette.light;
  const [currentAvatar, setCurrentAvatar] = useState("");
  const [username, setUsername] = useState(user?.username || "");
  const [avatar, setAvatar] = useState<ImagePicker.ImagePickerAsset | null>(
    null,
  );
  const [name, setName] = useState(user?.display_name || "");
  const [department, setDepartment] = useState(user?.department || "");
  const [year, setYear] = useState(user?.year || "");
  const [bio, setBio] = useState(user?.bio || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isUsername = !user?.username;
  const editing = Boolean(onCancel);
  useEffect(() => {
    if (!editing || !user?.username) return;
    const controller = new AbortController();
    void api<{ avatar_url: string }>(`/members/${user.username}/`, {
      signal: controller.signal,
    })
      .then((profile) => {
        if (!controller.signal.aborted) setCurrentAvatar(profile.avatar_url);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [editing, user?.username]);
  const choosePicture = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.9,
      });
      if (!result.canceled && result.assets[0]) setAvatar(result.assets[0]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not choose a picture.");
    }
  };
  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      if (editing && username !== user?.username) {
        const updated = await api<CampusUser>("/me/username/", {
          method: "POST",
          body: JSON.stringify({ username }),
        });
        updateUser(updated);
      }
      if (editing && avatar) {
        const body = new FormData();
        if (Platform.OS === "web" && avatar.file)
          body.append("file", avatar.file);
        else
          body.append("file", {
            uri: avatar.uri,
            name: avatar.fileName || "profile.jpg",
            type: avatar.mimeType || "image/jpeg",
          } as unknown as Blob);
        await api("/me/avatar/", { method: "POST", body, timeoutMs: 120000 });
      }
      const next = await api<CampusUser>(
        isUsername ? "/me/username/" : "/me/profile/",
        {
          method: isUsername ? "POST" : "PUT",
          body: JSON.stringify(
            isUsername
              ? { username }
              : { display_name: name, department, year, bio },
          ),
        },
      );
      updateUser(next);
      onComplete?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthPage
      dark={dark}
      embedded={editing}
      bottomInset={editing ? 112 : 0}
      eyebrow={
        editing
          ? "YOUR CAMPUS IDENTITY"
          : isUsername
            ? "01 / MAKE IT YOURS"
            : "02 / THE PERSON BEHIND THE PIXEL"
      }
      title={
        editing
          ? "Your profile.\nYour perspective."
          : isUsername
            ? "What should\nwe call you?"
            : "A little\nabout you."
      }
      subtitle={
        isUsername
          ? "Choose your unique campus handle. This is how people will find you—and you can use it to sign in."
          : "Bring your profile into focus. Your college email stays private."
      }
    >
      {isUsername ? (
        <>
          <Field
            dark={dark}
            editable={!busy}
            label="Your username"
            placeholder="e.g. frames.by.you"
            value={username}
            onChangeText={(value) => setUsername(value.toLowerCase())}
            maxLength={30}
            autoComplete="username-new"
          />
          <View style={s.notice}>
            <Text style={s.noticeText}>
              3–30 characters: letters, numbers, periods and underscores.
              Include a letter. No spaces, leading/trailing periods or
              consecutive periods. Your handle must be unique; official names
              are reserved.
            </Text>
          </View>
          <Text style={[s.muted, { color: theme.muted }]}>
            You can change your unique username from Edit profile.
          </Text>
        </>
      ) : (
        <>
          {editing && (
            <>
              <View
                style={{
                  flexDirection: "row",
                  alignItems: "center",
                  gap: 18,
                  marginBottom: 24,
                }}
              >
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Change profile picture"
                  disabled={busy}
                  onPress={() => void choosePicture()}
                  style={{
                    width: 84,
                    height: 84,
                    borderRadius: 42,
                    borderWidth: 2,
                    borderColor: palette.blue,
                    backgroundColor: theme.surface,
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden",
                  }}
                >
                  {avatar?.uri || currentAvatar ? (
                    <Image
                      source={{ uri: avatar?.uri || currentAvatar }}
                      resizeMode="cover"
                      style={{ width: 80, height: 80, borderRadius: 40 }}
                    />
                  ) : (
                    <Feather name="user" size={32} color={theme.muted} />
                  )}
                </Pressable>
                <View style={{ flex: 1, gap: 8 }}>
                  <Text
                    style={{
                      color: theme.text,
                      fontSize: 14,
                      fontWeight: "600",
                    }}
                  >
                    Profile photo
                  </Text>
                  <View style={{ alignSelf: "flex-start" }}>
                    <DesignedButton
                      compact
                      selected
                      disabled={busy}
                      onPress={() => void choosePicture()}
                    >
                      Change picture
                    </DesignedButton>
                  </View>
                </View>
              </View>
              <Field
                dark={dark}
                editable={!busy}
                label="Username"
                value={username}
                onChangeText={(value) => setUsername(value.toLowerCase())}
                maxLength={30}
                autoCapitalize="none"
              />
            </>
          )}
          <Field
            dark={dark}
            editable={!busy}
            label="Display name"
            placeholder="Your full name"
            value={name}
            onChangeText={setName}
            autoCapitalize="words"
            maxLength={80}
          />
          <Field
            dark={dark}
            editable={!busy}
            label="Department"
            placeholder="e.g. Computer Science"
            value={department}
            onChangeText={setDepartment}
            autoCapitalize="words"
            maxLength={80}
          />
          <Field
            dark={dark}
            editable={!busy}
            label="Year / designation (optional)"
            placeholder="e.g. Second year or Faculty"
            value={year}
            onChangeText={setYear}
            autoCapitalize="sentences"
            maxLength={30}
          />
          <Field
            dark={dark}
            editable={!busy}
            label="Bio (optional)"
            placeholder="What catches your eye?"
            value={bio}
            onChangeText={setBio}
            multiline
            autoCapitalize="sentences"
            maxLength={150}
          />
          <Text style={[s.muted, { color: theme.muted }]}>
            {bio.length}/150 · Visible to signed-in college members
          </Text>
        </>
      )}
      <Message text={error} error />
      <Action
        busy={busy}
        disabled={isUsername ? !username : !name.trim() || !department.trim()}
        onPress={() => void submit()}
      >
        {editing
          ? "Save changes"
          : isUsername
            ? "Claim your username"
            : "Step into PIXEL"}
      </Action>
      <Pressable
        disabled={busy}
        accessibilityRole="button"
        onPress={
          onCancel || (() => void logout().catch((e) => setError(e.message)))
        }
      >
        <Text
          style={[
            s.link,
            {
              textAlign: "center",
              marginTop: 14,
              color: dark ? "#93B4FF" : palette.blue,
              minHeight: 44,
            },
          ]}
        >
          {onCancel ? "Cancel" : "Sign out"}
        </Text>
      </Pressable>
    </AuthPage>
  );
}
