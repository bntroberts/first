---
name: ipb-talking-head-skill
description: "Edit Insurance Pro Blog (IPB) talking-head YouTube rough cuts into finished 1080p videos: branded zooms and pans, a name lower third, animated statistic call-outs, and licensed Storyblocks B-roll, delivered as a rendered MP4 plus a Premiere Pro-importable timeline. Use when Brandon asks to edit, finish, or add B-roll to an IPB video. Not for Yield to Reason videos, music, captions, or thumbnails."
metadata:
  author: Brandon Roberts
  version: '2.0'
  supersedes: ipb-talking-head-video (Perplexity, v1.0)
  connectors:
    - google_drive: Rough cuts arrive in the "Insurance Pro Blog Videos" Drive folder.
    - storyblocks: B-roll search and licensing (Brandon's account).
    - adobe: Optional speech cleanup and cloud rendering. This is Adobe Express/Firefly, not Premiere Pro desktop.
---

# IPB Talking-Head Video Editing

The Insurance Pro Blog (IPB) is Brandon Roberts' channel on cash value life insurance, annuities and retirement income. Its audience is high-income professionals, so the look is calm, credible and information-dense, never flashy.

Brandon cuts pauses and bad takes and adds music himself. You add the finishing layer — motion, graphics and B-roll — and deliver a rendered MP4 plus a timeline he can open in Premiere Pro to adjust.

If a video belongs to Yield to Reason, use the YTR skill instead.

## Scope

- **Do:**
  - Punch-in zooms and slow push-ins or pans.
  - One lower third near the start: "Brandon Roberts" over "THE INSURANCE PRO BLOG".
  - Animated data call-outs, only when he quotes a statistic.
  - B-roll from Storyblocks over selected lines (see `references/broll.md`).
- **Don't:**
  - Captions, or text that follows his speech.
  - Music or sound effects (Storyblocks audio included). His audio is never replaced or ducked.
  - Thumbnails, unless asked separately.

## What the tools can and can't do

Be accurate with Brandon about this:

- **Premiere Pro:** there is no direct control of the Premiere desktop app. Instead, deliver an FCP7 XML timeline (`File > Import` in Premiere) with the rough cut on V1, B-roll on V2 and the rendered graphics on V3, so he can nudge or swap anything. The MP4 is the finished version; the XML is for revisions he wants to make himself.
- **Storyblocks:** search, preview and license stock video. Every `get_download_url` call licenses the clip and logs a download on his account, so only call it for clips that are going into the cut.
- **Adobe connector:** `media_enhance_speech` can clean up voice audio, but only when Brandon asks for it. `video_render` handles 10 minutes at most; local ffmpeg is the default renderer.
- **YouTube:** the session's network may not reach youtube.com. Don't claim to have watched a reference video; ask Brandon to describe it or send a frame if style context is needed.

## Inputs

- **Rough cut:** an MP4 in the Google Drive folder "Insurance Pro Blog Videos" (ID `1t4jfnOhWLJ79FLWcmtJbQDblE2ueVFZU`).
- **Transcript:** Brandon supplies it. Do not create one yourself.
  - If it's missing, ask for it before planning edits. Ask for a timestamped export (SRT, VTT, or Descript/Premiere text with timecodes) that matches the final rough cut.
  - If he only has plain text, use it as the authoritative wording and get timings from an automatic word-timing pass on the audio. Tell him you did this.
- **Statistic sources:** IPB cites credible research (LIMRA, Morningstar, DOL, TIAA and similar). Put a source in `source_note` only when Brandon provides or confirms it. Never invent a citation, and list any unsourced stats in your delivery.
- **Teleprompter script:** when Brandon supplies it, its `[On screen: ...]` notes are the confirmed sources, and any `[B-roll: ...]` notes are B-roll requests that take priority over your own picks. Show a source on every data sequence and add a `source_tags` call-out whenever he mentions research without a stat card. Where the spoken words differ from the script, cards follow what he said; flag the difference.
- **Rendering engine:** `scripts/ipb_edit.py` (graphics, from the v1.0 Perplexity skill) and `scripts/broll_overlay.py` (B-roll). They need ffmpeg plus `pip install opencv-python-headless numpy pillow`. Fonts (Lato, PT Serif, both OFL-licensed) are in `assets/fonts/`.

## Workflow

1. **Download and check the cut.** Download from Drive, probe the resolution, frame rate and duration, and make a frame contact sheet. Done when the face position is known and `face_center` is updated if the setup has changed.
2. **Mark the moments.** From the transcript, list:
   - every quoted statistic (number, wording, timestamp);
   - lines worth emphasizing: hooks, key conclusions, contrasts, "here's the deeper reality" pivots;
   - B-roll candidates: concrete, visual nouns and scenarios (a couple reviewing paperwork, a retiree at a kitchen table, a hospital hallway for long-term care). Abstract lines and personal opinions stay on his face.
   Done when each statistic and B-roll candidate has a timestamp.
3. **Write the plan JSON.** Follow `references/edit-plan.md`, starting from a copy of `assets/example-plan.json`.
   - **Lower third:** about 0.3 s after he introduces himself, on screen for about 5 s.
   - **Roadmap:** when he previews the video's sections, show a `"style": "list"` data sequence with one numbered card per section, timed to when he names it.
   - **Statistics:**
     - Group stats spoken in one run into a single data sequence of up to 3 cards. A lone stat gets one card.
     - Give each sequence a `label` (topic category, such as "Annuities" or "By the numbers") and a short `title`.
     - Card labels paraphrase what he said. Never change a number or add data he didn't say.
   - **Zooms:** punch-in on strong lines, slow push-in through long explanations, and a reset at sentence or topic changes. Aim for a framing change about every 20–40 s, never during a data sequence or B-roll. Keep the motion measured; this audience is analytical.
   - **B-roll:** add a top-level `broll` array. Rules, search method and the field format are in `references/broll.md`.
4. **Source the B-roll.** Search Storyblocks, shortlist, check previews, then license and download only the final picks into `broll/`. If Brandon asked to approve B-roll first, send him the shortlist (timestamp, line, clip title, `details_url`) and wait before licensing anything.
5. **Check stills before rendering.** Run `--stills` at the lower third, each card's peak, a few zoom peaks and the middle of every B-roll insert, then look at them. Check for clipped or overlapping text, the face cut off at maximum zoom, unreadable cards, B-roll with visible logos, watermarks or text, and B-roll whose color clashes badly with his footage. Fix and re-check until every still is clean.
6. **Render.**
   - Graphics pass: `python3 scripts/ipb_edit.py plan.json`. For cuts over about 10 minutes, render parallel `--from/--to` chunks split outside any data sequence, join with ffmpeg's concat demuxer, and re-mux the original audio with `-c:a copy`.
   - B-roll pass: `python3 scripts/broll_overlay.py <graphics_render.mp4> plan.json -o "<final>.mp4"`. It overlays the clips full-frame, keeps the main audio untouched, and writes `<final>.xml` for Premiere.
   - Verify the duration matches the source, the audio stream is present, and spot-check a frame inside each B-roll window.
7. **Deliver.** Name the file "<original name> - Edited v1.mp4", bumping the version for revisions, and share it in chat along with the `.xml`; Brandon downloads them from there. Do not upload to Drive (uploads over about 50–100 MB fail through the connector). Summarize:
   - each data sequence and the zoom moments, with timestamps;
   - each B-roll insert: timestamp, the line it covers, Storyblocks clip title and ID;
   - unsourced stats;
   - what can be adjusted.

## Brand

These match the blog's colors and fonts (see `insurance-pro-blog-post`).

- **Colors:**
  - Navy #1B3A5C: name, titles, numbers, bottom rule.
  - Teal #1A7A6D: accents, dividers, category labels, bars, frame border.
  - Slate #2C3E50: card text.
  - Gold #C5922E: qualifier words only.
  - Warm White #F5F3EF: data-sequence background.
  - Stone #E8E4DD: card borders and bar tracks.
  - Muted Gray #888888: source line.
- **Fonts:** Lato (`assets/fonts/Lato-*.ttf`) for the name, titles and numbers. PT Serif (`assets/fonts/PT_Serif-*.ttf`) for card labels, subtitles and sources.
- **Layout:**
  - Data sequences use a light warm-white panel with white cards, each with a teal left accent and a soft shadow.
  - His shrunken frame sits top left with a white mat and a thin teal border.
  - No glow effects. That's the YTR look, not IPB.
- **B-roll look:** natural light, neutral-to-warm color, real-looking people (often 45–70), unhurried camera moves. No glossy-ad energy.

## Lasting defaults

- Source call-outs whenever research is mentioned (Brandon's request on "Annuities Love Hate"): `source_note` on sequences plus `source_tags` elsewhere.
- Use `chained` sequences for long stat runs and `display` for ratio-style values.
- Roadmap/agenda segments get a numbered `list` sequence (Brandon's request on "Annuities Love Hate").
- If the rough cut's framing differs from the default, set `face_center` and an explicit `pip_crop` that stays inside the frame (e.g. face [1020, 300] used `pip_crop` [370, 0, 1300, 731]).
- B-roll added Nov 2026 (v2.0). Default density and rules live in `references/broll.md`.

## Revisions

Edit the plan, check stills, re-render, and save as the next version. Re-use already-licensed B-roll files in `broll/` rather than downloading again. If Brandon asks for a lasting style change, update the defaults in the scripts or `references/broll.md` and note it under "Lasting defaults".
