# Loading states

- `LoadingImage` reserves the supplied media dimensions and shows the pixel wave inside the image frame until its source loads. A source change resets only that image's loading state. Errors replace the animation with an unavailable message.
- `PixelMotionLoader` uses PIXEL blue and the existing ivory/charcoal palette. Use `overlay` only inside a bounded media viewport; `size` supports thumbnails. Moments stop showing this loader after their first video frame, including during later buffering.
- `ContentSkeleton` provides list, profile, card, post and overview shapes. Use it for empty initial loads, keeping existing content during a refresh. Both animations respect reduced motion and clean up on unmount.

Page headers are fixed siblings of scrollable content. Full-page modals use no container transition so the header stays stationary. Keep content clipped below the header, and animate only the body or inset panels. `LiquidPage` keeps public page content centered at 600px; Admin Studio uses 1120px.
