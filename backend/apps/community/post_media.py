"""Ordered post images; the API never accepts arbitrary Drive file IDs here."""

from .media import delivery_url


def images(publication, viewer):
    if publication.kind != "post":
        return []
    return [
        {
            "id": str(index),
            "cover_url": delivery_url(publication, viewer, "thumbnail", media_index=index),
            "preview_url": delivery_url(publication, viewer, "preview", media_index=index),
            **publication.image_dimensions.get(file_id, {}),
        }
        for index, file_id in enumerate(publication.post_media)
    ]
