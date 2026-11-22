export type Person = {
  id: string;
  username: string;
  display_name: string;
  department: string;
  year: string;
  bio: string;
  role: string;
  avatar_url: string;
};
export type Member = Person & {
  saved_count?: number;
  followers: number;
  following: number;
  follow_state: string;
  mandatory: boolean;
  can_see_photos: boolean;
};
export type Publication = {
  images?: {
    id: string;
    cover_url: string;
    preview_url: string;
    width?: number;
    height?: number;
  }[];
  image_width?: number;
  image_height?: number;
  id: string;
  kind: string;
  title: string;
  caption: string;
  tag: string;
  cover_url: string;
  preview_url: string;
  video_url: string;
  author: Person;
  event_id: string;
  event_title: string;
  liked: boolean;
  saved: boolean;
  like_count: number;
  comment_count: number;
  created_at: string;
};
export type CampusEvent = {
  photo_count?: number;
  id: string;
  title: string;
  tag: string;
  description: string;
  venue: string;
  starts_at: string;
  ends_at: string;
  cover_url: string;
  form_url: string;
};
export type Page<T> = { count?: number; results: T[]; next: string | null };
export type Discussion = {
  id: number;
  text: string;
  parent_id: number | null;
  author: Person;
  like_count: number;
  liked: boolean;
  can_delete: boolean;
};
