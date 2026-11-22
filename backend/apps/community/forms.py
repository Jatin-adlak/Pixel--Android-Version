from django import forms

from .media import drive_session
from .models import DriveFolder, Event, Publication


class PublicationForm(forms.ModelForm):
    cover_upload = forms.FileField(
        required=False, help_text="Optional custom JPEG/PNG/WebP cover, uploaded to Drive."
    )
    upload = forms.FileField(
        required=False,
        help_text="Upload an image for a post/photo or an MP4 video for a moment (up to 100 MB). Connect the Pixel account first for My Drive uploads.",
    )
    drive_media = forms.ChoiceField(
        required=False,
        label="Media from the Posts / Moments Drive folder",
        help_text="Upload the original in Drive first, then select it here. Drive thumbnails provide the default cover. You may override the cover URL below.",
    )

    class Meta:
        model = Publication
        exclude = ["author"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [("", "Use the existing Drive file ID or external URLs")]
        self.media_kinds = {}
        try:
            with drive_session() as session:
                for folder in DriveFolder.objects.all():
                    token = None
                    while True:
                        response = session.get(
                            "https://www.googleapis.com/drive/v3/files",
                            params={
                                "q": f"'{folder.folder_id}' in parents and trashed = false",
                                "fields": "nextPageToken,files(id,name,mimeType)",
                                "pageSize": 1000,
                                "supportsAllDrives": "true",
                                "includeItemsFromAllDrives": "true",
                                **({"pageToken": token} if token else {}),
                            },
                            timeout=20,
                        )
                        response.raise_for_status()
                        data = response.json()
                        prefix = "video/" if folder.kind == "moment" else "image/"
                        for file in data.get("files", []):
                            if file["mimeType"].startswith(prefix):
                                choices.append(
                                    (file["id"], f"{folder.get_kind_display()} / {file['name']}")
                                )
                                self.media_kinds[file["id"]] = folder.kind
                        token = data.get("nextPageToken")
                        if not token:
                            break
        except Exception:
            self.fields[
                "drive_media"
            ].help_text = "Drive listing is unavailable. Check credentials/folder access, or enter a known accessible file ID."
        self.fields["drive_media"].choices = choices

    def clean(self):
        data = super().clean()
        selected = data.get("drive_media")
        if selected:
            if self.media_kinds.get(selected) != data.get("kind"):
                self.add_error(
                    "drive_media", "Choose media from the folder matching the publication kind."
                )
            self.instance.drive_file_id = selected
            data["drive_file_id"] = selected
        upload = data.get("upload")
        folder = (
            data.get("event").drive_folder_id
            if data.get("kind") == "photo" and data.get("event")
            else DriveFolder.objects.filter(kind=data.get("kind"))
            .values_list("folder_id", flat=True)
            .first()
        )
        if upload and not self.errors:
            from .drive import upload_media

            if selected:
                self.add_error("upload", "Choose either a Drive file or a new upload.")
                return data
            folder = (
                data.get("event").drive_folder_id
                if data.get("kind") == "photo" and data.get("event")
                else DriveFolder.objects.filter(kind=data.get("kind"))
                .values_list("folder_id", flat=True)
                .first()
            )
            try:
                file_id = upload_media(upload, folder, data.get("kind"))
                self.instance.drive_file_id = file_id
                data["drive_file_id"] = file_id
            except (ValueError, RuntimeError) as exc:
                self.add_error("upload", str(exc))
        cover = data.get("cover_upload")
        if cover and not self.errors:
            from .drive import upload_media

            try:
                file_id = upload_media(cover, folder, "photo")
                self.instance.cover_drive_file_id = file_id
                data["cover_drive_file_id"] = file_id
            except (ValueError, RuntimeError) as exc:
                self.add_error("cover_upload", str(exc))
        return data


class EventForm(forms.ModelForm):
    cover_upload = forms.FileField(
        required=False,
        help_text="JPEG/PNG/WebP event cover. It goes into this event’s Drive folder.",
    )

    class Meta:
        model = Event
        fields = "__all__"

    def clean(self):
        data = super().clean()
        cover = data.get("cover_upload")
        if cover and not self.errors:
            from .drive import upload_media

            try:
                file_id = upload_media(cover, data.get("drive_folder_id"), "photo")
                self.instance.cover_drive_file_id = file_id
                data["cover_drive_file_id"] = file_id
            except (ValueError, RuntimeError) as exc:
                self.add_error("cover_upload", str(exc))
        return data
