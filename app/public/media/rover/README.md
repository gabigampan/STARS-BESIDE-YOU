# Rover mission video

**Credit line to show in the app:**
"Rover mission video: 3D simulation by the Stars Beside You team (not real footage)"

This is a 3D simulation made by the team (a VIPER-like rover driving on a lunar surface, with an on-screen data panel in Spanish). It is **not real footage** and must never be described as such.

## Content is unaltered

The outputs are re-encodes of the team's video with nothing changed in the picture or the timing: no cropping, scaling, overlays, filters, re-timing or frame-rate change. Each output has the same 900 frames in the same order at 30 fps (30.000 s), checked by comparing frame index against frame index (see Checks). The only container-level difference: the source's first frame has a timestamp of 0.067 s (a 2-frame start offset in the WhatsApp file), while the outputs start at 0.000 s. The frame durations (1/30 s) and total duration are the same.

## Files

| File | What it is | Size (bytes) | Duration | Codec | Resolution |
|---|---|---|---|---|---|
| `rover.mp4` | Main video, H.264 High@L4.0, yuv420p, 30 fps, no audio, moov atom at the front (faststart) | 2,339,200 (2.34 MB) | 30.000 s, 900 frames | h264 (High) | 1280x720 |
| `rover.webm` | Alternative source, VP9 profile 0, yuv420p, 30 fps, no audio | 2,216,942 (2.22 MB) | 30.000 s, 900 frames | vp9 | 1280x720 |
| `rover-poster.jpg` | Poster frame: source frame 600 (t = 20 s), rover fully visible, panel readable | 58,880 | n/a | mjpeg | 1280x720 |
| `rover-poster.webp` | Same frame as WebP (quality 90) | 37,986 | n/a | webp | 1280x720 |
| `rover.en.vtt` | English descriptive captions (12 cues, 0 to 30 s) | 1,607 | 30 s | WebVTT | n/a |
| `rover.es.vtt` | Spanish (Spain) descriptive captions (12 cues, 0 to 30 s) | 1,755 | 30 s | WebVTT | n/a |

Suggested markup:

```html
<video controls playsinline preload="metadata" poster="/media/rover/rover-poster.webp">
  <source src="/media/rover/rover.webm" type="video/webm">
  <source src="/media/rover/rover.mp4" type="video/mp4">
  <track kind="captions" src="/media/rover/rover.en.vtt" srclang="en" label="English">
  <track kind="captions" src="/media/rover/rover.es.vtt" srclang="es" label="Español">
</video>
```

## Source

- File: `WhatsApp_Video_2026-11-14_at_20.02.19.mp4` (team upload)
- sha256: `3396d9bc8b5c6be37a6a5a0dfccc881104fc651efbd3a8d49e9668f4edd73e4f`
- Size: 5,237,479 bytes
- H.264 High@L3.1, yuv420p, 1280x720, 30/1 fps, 30.000 s, 900 frames, ~1.39 Mb/s, no audio, MP4

## Commands (ffmpeg 6.1.1)

`SRC` is the source file above.

```sh
# rover.mp4 (CRF 22 chosen from a sweep of 20/22/24/26, see below)
ffmpeg -i "$SRC" -map 0:v:0 -an -c:v libx264 -preset veryslow -tune animation -crf 22 \
  -profile:v high -level:v 4.0 -pix_fmt yuv420p -fps_mode passthrough -movflags +faststart rover.mp4

# rover.webm (two-pass constant quality, CRF 30 chosen from 24/30/34)
ffmpeg -i "$SRC" -map 0:v:0 -an -c:v libvpx-vp9 -crf 30 -b:v 0 -pix_fmt yuv420p -row-mt 1 -tile-columns 2 \
  -deadline good -cpu-used 1 -pass 1 -passlogfile vp30 -f null /dev/null
ffmpeg -i "$SRC" -map 0:v:0 -an -c:v libvpx-vp9 -crf 30 -b:v 0 -pix_fmt yuv420p -row-mt 1 -tile-columns 2 \
  -deadline good -cpu-used 1 -pass 2 -passlogfile vp30 rover.webm

# posters (frame index 600 = 20 s)
ffmpeg -i "$SRC" -vf "select=eq(n\,600)" -frames:v 1 -q:v 2 rover-poster.jpg
ffmpeg -i "$SRC" -vf "select=eq(n\,600)" -frames:v 1 -c:v libwebp -quality 90 rover-poster.webp
```

Quality versus the source (frame index against frame index, Y/U/V PSNR average and SSIM All):

| Encode | Size | PSNR avg (min) | SSIM |
|---|---|---|---|
| x264 CRF 20 | 3.16 MB | 52.2 dB (49.4) | 0.9976 |
| **x264 CRF 22 (used)** | **2.34 MB** | **50.2 dB (47.7)** | **0.9967** |
| x264 CRF 24 | 1.68 MB | 48.6 dB | 0.9959 |
| x264 CRF 26 | 1.26 MB | 47.3 dB | 0.9950 |
| **VP9 CRF 30 (used)** | **2.22 MB** | **50.0 dB (40.8)** | **0.9968** |

Re-encoding beat the source's size (5.24 MB) at visually identical quality (side-by-side crops of the panel text and the wheels showed no visible difference), so the original was not remuxed.

## Captions

The video has no speech; the captions describe what is shown. Values were transcribed from frames extracted every 2.5 s (plus extra frames every 0.5 s at the start and end to see how the panel updates). Each cue gives the panel values shown at its start time; the panel counts up continuously (distance by about 0.1 m every 0.5 s). Speed (20 cm/s), wheels (7.6 rpm), sun elevation (21.1°) and gravity (1.62 m/s²) read the same in every frame sampled. Every value in the frames was legible; none were guessed. The panel's own "Tiempo" clock runs from 00:05 to 00:35, which is the simulation's clock, not the video's position. The first cue of each track says that it is a 3D simulation made by the team and not real footage.

## Checks

- Frame count and duration: source 900 frames / 30.000 s; rover.mp4 900 / 30.000 s; rover.webm 900 / 30.000 s; 1/30 s per frame in all three.
- Same picture: frames 90, 450 and 810 (3 s, 15 s, 27 s) taken from the source and from each output match (RGB PSNR 45.8 to 46.3 dB for mp4, 44.3 to 45.7 dB for webm; a source frame against a different source frame gives 16 to 19 dB, and a 2-frame shift gives about 35 dB).
- Faststart: in rover.mp4 the `moov` box is at byte 36, before `mdat`.
- WebVTT: both files have the `WEBVTT` header, a blank line after it, 12 cues with increasing timestamps, no overlaps, ending at 00:30.000; both parse in ffmpeg (webvtt demuxer).
