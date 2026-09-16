Built-in imagegen generated foreground-mask.png and speaking.png from xingxuan-readable.png.

Mask prompt: Exact aligned white foreground silhouette on black, preserving full body and white sleeves, no repositioning. Used as CSS luminance mask; original source remains intact.

Speaking prompt: Change only mouth to gently open speaking expression, preserving face tilt, body and canvas. Only a small elliptical mouth region is shown as an overlay.

Audio amplitude envelopes sampled every 50 ms from supplied WAV files drive mouth opening at current playback time. Silence, pause, end and navigation close the mouth. This is amplitude-driven animation, not phoneme alignment.
