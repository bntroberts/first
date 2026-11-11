# B-roll for IPB Talking-Head Videos

B-roll supports what Brandon is saying; it never replaces him. The viewer should feel they're still in a conversation with an advisor, not watching an ad.

## Where B-roll goes

- **Density:** about one insert every 45–90 s. A 12-minute video usually gets 8–14 inserts.
- **Length:** 3–7 s each. Cut or dissolve back to his face before the end of the thought, so the conclusion lands on him.
- **Good spots:**
  - Concrete scenarios he describes ("a 62-year-old couple trying to decide when to claim Social Security").
  - Examples, stories and hypotheticals.
  - Long explanations where the zoom plan alone would feel static.
  - Lines the teleprompter script tags `[B-roll: ...]` (these always win).
- **Never:**
  - The first 15 s (the hook stays on his face) or the final call to action.
  - During the lower third, a data sequence, a `source_tags` call-out, or within 1 s of either side of one.
  - Over a punch-in zoom: the zoom is the emphasis there.
  - Back-to-back inserts with less than 10 s of his face between them.
  - Over "I", "my clients", "here's what I'd do" and other first-person credibility lines.

## Choosing clips

- **Prefer:** couples or individuals 45–70 at a kitchen table, in a home office, or meeting an advisor; reviewing documents or a laptop; calm everyday retirement life (walking, grandchildren, gardening); hospital or care settings for long-term care topics; calculators and paperwork close-ups; neutral office and city establishing shots.
- **Avoid (clichés and compliance risks):**
  - Falling money, cash piles, gold bars, piggy banks, dollar-sign animations.
  - Flashing stock tickers and trading screens, unless he's talking about market volatility, and even then keep it brief.
  - Yachts, sports cars, champagne: anything implying guaranteed wealth.
  - Visible logos, brand names, readable on-screen text, watermarks, or anything that looks like a real insurer's or bank's documents.
  - Footage of a recognizable public figure or editorial-only clips.
  - Staged-looking "business people high-fiving" stock.
- **Technical:** horizontal, HD or 4K, 24/25/30 fps (match the cut when possible), talent-released when people's faces are visible. Avoid clips with hard cuts inside the usable section.

## Searching Storyblocks

1. For each candidate line, write a short visual brief: subject, action, setting (e.g. "older couple / reviewing bills / kitchen table").
2. Call `search_videos` with:
   - `keywords`: the full brief.
   - `required_keywords`: the main subject noun, singular ("couple", "nurse", "calculator").
   - `orientation: "horizontal"`, `quality: "HD"` (or `"4K"`), `content_type: "footage"`.
   - `has_talent_released: true` when people are featured; `is_editorial: false`.
   - `min_duration` of at least the insert length plus 1 s.
   - `results_per_page` around 10–15. Try `warmth: "warm"` or `"neutral"` if results look cold or clinical.
3. If results are weak, use `get_related_terms` for alternative wording, or `get_similar_videos` / `get_same_shoot_items` from the best hit (same-shoot clips also help when two inserts should feel related).
4. Shortlist 2–3 per slot and look at preview thumbnails or frames. Pick the one that best matches the line and IPB's calm look.
5. License and download only the final picks with `get_download_url` (`contentClass: "videos"`). Each call logs a download, so never call it to look at formats (`get_stock_item_details` with `extended: "download_formats"` does that) and never re-download a clip already in `broll/`. Download promptly: the signed URL expires in about 30 minutes and must be used exactly as returned.
6. Save as `broll/<stockItemId>.mp4` and record the ID and title in the plan.

## Plan format

Add a top-level `broll` array to the plan JSON:

```json
"broll": [
  {
    "start": 74.2,
    "end": 79.6,
    "file": "broll/123456.mp4",
    "source_in": 1.5,
    "move": "push",
    "storyblocks_id": 123456,
    "title": "Senior couple reviewing paperwork at kitchen table",
    "line": "Most couples sit down at the kitchen table with a stack of statements..."
  }
]
```

- `start` / `end`: seconds on the edited timeline.
- `source_in`: where to start in the stock clip (skip the clip's first second, which is often a camera settle).
- `move`: `"none"`, `"push"` (slow 100%→106% zoom), or `"pull"` (106%→100%). Default `"push"`; use `"none"` if the clip already has camera movement.
- `fade`: optional dissolve length in seconds (default 0.25). Use `0` for a hard cut.
- `title`, `storyblocks_id`, `line`: for the delivery summary and the Premiere XML.

`scripts/broll_overlay.py` validates these rules where it can (overlaps, minimum gap, clip long enough) and refuses to render if they fail.
