export type CampusUser = {
  id: string;
  email: string;
  username: string | null;
  role: "Administrator" | "Faculty" | "Student";
  display_name: string;
  department: string;
  year: string;
  bio: string;
  email_verified: boolean;
  profile_completed: boolean;
  tour_completed: boolean;
  onboarding_step: "username" | "profile" | "tour" | "complete";
};
export type PublicProfile = Pick<
  CampusUser,
  "id" | "username" | "display_name" | "department" | "year" | "bio" | "role"
>;
export type AuthConfig = {
  domain: string;
  google_enabled: boolean;
  password_reset_enabled: boolean;
  privacy_version: string;
  terms_version: string;
  privacy: string;
  terms: string;
  csrf_token: string;
};
export type PolicyInput = {
  privacy_accepted: boolean;
  terms_accepted: boolean;
  privacy_version: string;
  terms_version: string;
};
export type Tokens = { access: string; refresh?: string; user: CampusUser };
