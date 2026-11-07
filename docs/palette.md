# Palette

The colours of the README banner and where each one comes from. The photos are in `docs/palette/sources/`, with their licences in `SOURCES.md`. `docs/palette/research.md` records every sample, including colours the banner does not use, so a later frontend can draw on the same set.

## Method

The method follows the hansard repo's `docs/palette.md`.

1. A worker fetched openly licensed photos of the former Supreme Court from Wikimedia Commons on 7 November 2026. The building is now the Supreme Court Wing of National Gallery Singapore.
2. The sampling script runs k-means (k = 3) on a crop box around one object and records each cluster's hex and share of the crop. Before use it reproduced hansard's gown sample, #8d0f15 at 44.2% against the recorded #8d0f14 at 44%.
3. A banner colour keeps the sample's OKLCH hue and moves lightness until it reaches the contrast of openhansard's banner, 5.45:1 on #ffffff and 6.69:1 on #0d1117. Chroma changes only where this table says so.

## Sources

Crop boxes are fractions of the image: left, top, right, bottom.

| Colour | What it is | Source |
|---|---|---|
| #bdbbb3 | Fluted stone shaft, lit face, interior | `column-capital.jpg`, box 0.5,0.84,0.78,0.99, 33.3% |
| #bce0d7 | Copper dome, lit | `dome.jpg`, box 0.36,0.405,0.66,0.46, 35.2% |

## Banner colours

| Name | Light | Ratio on #ffffff | Dark | Ratio on #0d1117 | Parent |
|---|---|---|---|---|---|
| `stone` | #6b6962 | 5.49:1 | #9b9992 | 6.64:1 | #bdbbb3, chroma kept |
| `patina` | #087767 | 5.46:1 | #42aa96 | 6.69:1 | #bce0d7, chroma raised from 0.04 to 0.10 |
| Name | #1f2328 | 15.80:1 | #f0f6fc | 17.39:1 | openhansard's banner |

Patina's chroma is raised because at the sample's own 0.04 the colour is a dull grey-teal (#4f7069). The banner's green is therefore stronger than the dome.

## Banner

Royce picked this draft from five on 7 November 2026, over a recommended ruled block of Acts by decade. [ADR 0006](adr/0006-identity-from-the-former-supreme-court-facade.md) says why the facade.

- It shares openhansard's banner in these ways: a 1280 by 320 canvas, no background, the mark's square, capitals as tall as the mark, and the name's colours. It runs from x 64 to x 1209, and its capitals are 106 px tall.
- The name is Barlow Condensed Light and Bold, outlined to paths, because openhansard's banner uses it. OPEN LAW was ruled out because OpenLaw is a separate source.
- The six columns are counted from `front-cephoto.jpg`, box 0.33,0.60,0.47,0.74: a pair, two singles, a pair. `front-2014.jpg` agrees.
- The dome and pediment are sized by eye. The side blocks are drawn as plain wall, though the real wings have colonnades, which were not counted across the whole front.
- Patina is the mark's second colour at full strength. It misses openhansard's second tone, about 2.25:1 and 11.77:1, because the dome has to read beside the stone.

No State arms, court seal, scales, gavel or figures from the Allegory of Justice relief appear in the banner or are sampled. Some source photos show the relief, as whole-building photos do.

## Caveats

- Both samples are one exposure of one surface. The dome crop is lit and close to clipping, and the stone crop is indoors.
- The hansard repo's party-colour rule puts neither colour near a party colour.
- `dome.jpg` and the other Flickr-origin photos carry the licence their Commons pages state. The Flickr pages were not rechecked.
