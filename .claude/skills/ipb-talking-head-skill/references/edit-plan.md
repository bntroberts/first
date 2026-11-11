# Edit plan schema (scripts/ipb_edit.py)

All times are seconds on the rough cut's timeline. Copy `assets/example-plan.json` (the YTR-approved timing applied to IPB styling) and replace values.

```json
{
  "source": "/abs/path/rough-cut.mp4",
  "output": "<Video Title> - Edited v1.mp4",
  "face_center": [975, 380],
  "lower_third": {"text": "Brandon Roberts", "subtitle": "The Insurance Pro Blog", "in": 4.05, "out": 8.9},
  "zooms": [[start, end, zoom_from, zoom_to], ...],
  "data_sequences": [{
    "in": 13.95, "out": 31.25,
    "label": "By the numbers", "title": "Retirement Anxiety", "subtitle": "",
    "source_note": "Source: <publisher, study, year>",
    "pip_crop": [325, 14, 1300, 731],
    "stats": [{"t": 14.62, "value": 51, "suffix": "%", "qualifier": "Nearly",
               "label": "of Americans worry about outliving their savings"}]
  }]
}
```

## Fields
- `face_center`: Brandon's face in 1920×1080 source pixels. Zooms move toward it, and it is the default center for the shrunken top-left frame. Measure it from a still; in the v1 studio setup it was about [975, 380].
- `lower_third`: shown once. Name is navy Lato and the `subtitle` line is teal letter-spaced caps (default "The Insurance Pro Blog"). `in` = shortly after he introduces himself; `out` about 5 s later. The bar auto-sizes to the text.
- `zooms`: ordered and non-overlapping. Between keyframes the zoom holds the last `zoom_to`.
  - Punch-in: 0.35–0.4 s ease, 1.0→1.12–1.16.
  - Slow push-in: 3–8 s, 1.0→1.06–1.08.
  - Reset: 0.4 s back to 1.0, placed in a pause or at a sentence change.
- `data_sequences`:
  - The frame shrinks over 0.8 s starting at `in` and grows back over 1.0 s starting at `out`.
  - Set `in` about 0.6 s before the first stat is spoken. Set `out` after he finishes discussing the stats.
  - Never overlap a sequence with a zoom keyframe; the zoom state at `in` is the starting framing.
  - `pip_crop` is optional.
  - `label` = small teal caps above the title (like the blog's category label). `title` = navy Lato headline, which auto-shrinks to fit. `subtitle` = optional one-line PT Serif description under the teal divider.
  - `source_note` is optional and appears bottom-left. Leave it empty unless Brandon provides or confirms the source.
- `stats`: 1–3 per sequence works best; 4 fit but are tight.
  - `t`: the moment the number is spoken. The card slides in and the number counts up over 1.1 s.
  - `value`, `prefix` (for example "$"), `suffix` (default "%", use "" for none), `decimals`.
  - `qualifier`: a small gold word above the number, such as "Nearly", "Over" or "Up to".
  - `label`: about 4–12 words.
  - `bar`: defaults to true for percentages. `bar_fraction` (0–1) overrides the fill amount.
  - Set `bar: false` when the bar would mislead, for example on a percentage-change figure.

## Source tags and chaining
- `source_tags`: `[{"in", "out", "text", "label"}]`. A small white card bottom-left with a teal accent, teal caps `label` (default "Research") and the citation in PT Serif. Use it whenever he mentions research that has no stat card, about 6–10 s from the mention. Hidden during data sequences; never overlap one (allow 0.6 s fade-out).
- `chained: true` on a data sequence keeps the frame shrunk from the previous sequence. Set its `in` equal to the previous `out`; the panel dips to blank and the new title and cards fade in. Use it to run more than 3 stats in one stretch without the frame bouncing.
- `display` on a stat: static text (for example "1 in 4", "2/3", "13–24", "4th") that fades in instead of counting up. Use `bar_fraction` if a bar is wanted.
- `"style": "list"` on a data sequence renders numbered agenda cards instead of stats (up to 5). Each item: `{"t", "num", "label", "sub"}`; `label` is a short navy section name, `sub` a one-line PT Serif description. Use it for the roadmap/overview segment.
- Keep each sequence's `out` at least about 1.8 s after its last stat's `t` so the count finishes.

## Commands
- Stills: `python3 scripts/ipb_edit.py plan.json --stills 6,20,25`. Fast; writes `still_<t>.png`.
- Preview a range: `--from 12 --to 33 --out preview.mp4`.
- Full render: `python3 scripts/ipb_edit.py plan.json`. Expect about 6–8 minutes of render time per minute of footage.

The script scales or crops non-1080p input to 1920×1080, keeps the source frame rate, and copies the original audio untouched on full renders.
