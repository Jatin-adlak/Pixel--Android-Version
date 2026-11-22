import type { ImagePickerAsset } from "expo-image-picker";
export type AdminEvent = {
  id: string;
  title: string;
  tag: string;
  description: string;
  venue: string;
  starts_at: string;
  ends_at: string;
  cover_url: string;
  cover_preview_url?: string;
  cover_drive_file_id: string;
  drive_folder_id: string;
  form_url: string;
  published: boolean;
  spotlight: boolean;
  sync?: {
    last_success_at: string | null;
    error: string;
    photos: number;
  } | null;
};
export type AdminPublication = {
  images?: { id: string; cover_url: string; preview_url: string }[];
  id: string;
  title: string;
  kind: string;
  event: string;
  event_title: string;
  caption: string;
  tag: string;
  published: boolean;
  cover_url: string;
  cover_preview_url?: string;
  cover_drive_file_id: string;
  drive_file_id: string;
  original_url: string;
  preview_url: string;
  available: boolean;
};
export type AdminMember = {
  id: string;
  email: string;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  email_verified: boolean;
  department: string;
  year: string;
};
export type ModerationComment = {
  id: number;
  username: string;
  text: string;
  publication_title: string;
  created_at: string;
  publication: string;
  parent: number | null;
};
export type CommentGroup = {
  id: string;
  title: string;
  kind: string;
  comment_count: number;
  latest_comment_at: string;
};
export type Summary = {
  events: number;
  posts: number;
  moments: number;
  photos: number;
  members: number;
  comments: number;
  drive_connected: boolean;
  spotlights: number;
  published: number;
  drafts: number;
  unavailable: number;
  likes: number;
  saves: number;
  upcoming: number;
  sync: { errors: number; last_success_at: string | null };
  recent: {
    id: string;
    title: string;
    kind: string;
    published: boolean;
    available: boolean;
    created_at: string;
  }[];
};
export type Storage = {
  connected: boolean;
  folders: { kind: string; folder_id: string }[];
  connect_url: string;
};
export type MediaAsset = ImagePickerAsset;
