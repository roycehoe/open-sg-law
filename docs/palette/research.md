# README banner palette research

Source photos and colour samples for the open-sg-law README banner. The method is the hansard repo's (`docs/palette.md`, Method; `docs/palette/research.md`). The photos are in `docs/palette/sources/` with one row each in `docs/palette/sources/SOURCES.md`. Nothing here is a chosen colour: the pick is Royce's.

Three rules applied throughout.

1. Open licence only. Each licence was read from the file's Commons metadata, not from memory, and the author is recorded as Commons prints it.
2. No marks. The brief rules out State arms, the court seal, scales, a gavel and traced figures from the Allegory of Justice relief. Every crop was saved and viewed; none holds a person, State arms, seal, signage or logo. Photos that show such things elsewhere in the frame are listed per photo below, and none of those regions was cropped.
3. Colours only. The Allegory photo is sampled on plain cornice stone, never on the figures.

Crop boxes are fractions of the image as committed: left, top, right, bottom. Shares are the cluster's share of the crop. OKLCH is computed from the cluster hex. Hex values here are as measured; none was adjusted by eye. Hex, box and share are measured. The labels on minor clusters (under about 10%) are guesses at what the cluster is.

## Method check

Before use, the sampler was run on a hansard photo with a known value. File: `hansard/docs/palette/sources/speaker-ceremonial-gown-01.jpg` (1200 x 1600 px), box 0.44, 0.40, 0.47, 0.85, the box of source S1 in `docs/palette.md` Version 1.

| | Recorded in hansard | This sampler |
|---|---|---|
| Gown red satin, lit | `#8d0f14`, 44% (S1) | `#8d0f15`, 44.2% |
| Gown red satin, shaded | `#62090b`, 51% (S2) | `#62090b`, 51.2% |
| Third cluster | not recorded | `#110809`, 4.7% |

The lit red differs by 1 in the blue channel. `docs/palette.md` Method step 2 (current palette) records the same `#8d0f15` at 44.2%, so this agrees with hansard's own later run. The hansard repo holds no sampling script, so this one was written for this run: pure-Python k-means (k = 3, k-means++ start) on the crop's pixels, subsampled to 30,000 evenly spaced pixels when larger. PIL has no k-means, and the single seeded start is not stable: seed 1 gave `#870d13` at 56.9% and seeds 2 and 3 gave a 94% cluster. The sampler therefore runs ten seeds and keeps the run with the lowest within-cluster squared error. That rule gave the match above. Every sample below used it. Run under `nice -n 10`, one job at a time.

## How the photos were fetched

Commons only, User-Agent `open-sg-law-banner-research/0.1`, at least 11 s between requests, no 429 seen. The first pass asked the API for 2000 px thumbnails, which returned copies up to 3840 px wide (the API ignored the width). Those were replaced with the 1920 px thumbnail (`.../thumb/.../1920px-<name>`; Commons accepts only fixed widths and 2000 is not one). No file wider than 1920 px is kept. Scripts are in the session scratchpad `palette-tools/`.

## Party colours to stay clear of

Copied from `hansard/docs/palette/research.md`. They were not checked against the parties' own materials.

| Party | Colours | What to avoid |
|---|---|---|
| PAP | White, with a red lightning bolt in a blue circle | White plus red plus blue as a set; a blue disc with a red mark |
| WP | Light blue and white | Light blue as a primary or large fill |
| PSP | Red and white | Red with white as a brand pair |
| SDP | Red and blue | Red beside blue as a brand pair |

A colour is called near here if its OKLCH hue is within 30 degrees of a reference red (crest red 22.3, gown red 26.5) or the reference blue (sign blue 249.4) and its chroma is above about 0.08. Pale tints and neutrals are not near. The reference hues come from the hansard note.

## Findings by photo

### `dome.jpg`

The copper dome over the central block, lit from the left under thin cloud. Cluster 1 is close to white: the sunlit patina is nearly overexposed. Kok Leng Yeo from Singapore, CC BY 2.0. Citation: SOURCES row `dome.jpg`; https://commons.wikimedia.org/wiki/File:Dome-OldSupremeCourtBuilding-Singapore-20071013.jpg

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#d6f7ef` | Lit copper sheeting, near-clipped | 0.36, 0.405, 0.66, 0.46 | 60.5% | Cloudy daylight | L 0.950, C 0.036, h 179.3 |
| `#bce0d7` | Lit copper sheeting, mid | 0.36, 0.405, 0.66, 0.46 | 35.2% | Same | L 0.878, C 0.040, h 178.5 |
| `#769790` | Seams and shaded ribs | 0.36, 0.405, 0.66, 0.46 | 4.3% | Same | L 0.649, C 0.038, h 180.6 |

Incidental marks: a small finial figure on the lantern, outside the crop. Not cropped. A first box on the right flank (0.69, 0.43, 0.77, 0.50) gave `#8da9b7` at 64.1% because sky filled the box, so it was rejected and is not used.

### `front-2014.jpg`

Portico and side wall in flat overcast light. Sampled once, on one shaft; the shaft is in shade. Jacklee, CC BY-SA 4.0. Citation: SOURCES row `front-2014.jpg`; https://commons.wikimedia.org/wiki/File:Old_Supreme_Court_Building,_Singapore_-_20141101.JPG

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#67605a` | Portico column shaft, shaded | 0.68, 0.62, 0.71, 0.86 | 52.2% | Overcast, column in shade | L 0.494, C 0.013, h 63.2 |
| `#544e47` | Same shaft, deeper flutes | 0.68, 0.62, 0.71, 0.86 | 32.2% | Same | L 0.427, C 0.014, h 71.7 |
| `#332f2b` | Flute shadows | 0.68, 0.62, 0.71, 0.86 | 15.6% | Same | L 0.308, C 0.009, h 67.5 |

Incidental marks: the Allegory of Justice relief fills the pediment, and a tower stands behind the building. Neither was cropped. The crop is a 57-pixel-wide strip on one column.

### `front-cephoto.jpg`

The building seen from across the river, with the dome, the portico and the National Gallery roofs. Not sampled; it is the straight-on view used for the column count. CEphoto, Uwe Aranas, CC BY-SA 3.0. Citation: SOURCES row `front-cephoto.jpg`; https://commons.wikimedia.org/wiki/File:Singapore_Old-Supreme-Court-Building-01.jpg

Incidental marks: a signboard reading SOMERSET on a building, a small flag at the far left edge, banners on the bridge, a boat. Nothing from this photo is cropped for colour.

### `column-capital.jpg`

An interior corner under the dome: a white plaster arch springing from a plaster block, an ebony-dark capital and a fluted pale stone shaft. The shaft box straddles lit flutes and their shadows. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `column-capital.jpg`; https://commons.wikimedia.org/wiki/File:Column_capital,_Old_Supreme_Court_Building,_Singapore_-_20101010.JPG

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#adafa9` | White plaster arch face | 0.42, 0.02, 0.58, 0.28 | 57.4% | Interior daylight, shaded | L 0.751, C 0.009, h 121.7 |
| `#9e9f98` | Plaster, slightly darker | 0.42, 0.02, 0.58, 0.28 | 37.7% | Same | L 0.700, C 0.010, h 113.2 |
| `#767675` | Plaster edge shadow | 0.42, 0.02, 0.58, 0.28 | 4.9% | Same | L 0.566, C 0.002, h 106.4 |
| `#62584f` | Fluted stone, flute shadow | 0.5, 0.84, 0.78, 0.99 | 35.9% | Interior light | L 0.467, C 0.019, h 64.3 |
| `#bdbbb3` | Fluted stone, lit face | 0.5, 0.84, 0.78, 0.99 | 33.3% | Same | L 0.791, C 0.011, h 95.2 |
| `#877e72` | Fluted stone, mid | 0.5, 0.84, 0.78, 0.99 | 30.7% | Same | L 0.598, C 0.021, h 75.2 |
| `#131212` | Capital, near black | 0.4, 0.66, 0.68, 0.78 | 73.8% | Interior, dim | L 0.183, C 0.002, h 17.3 |
| `#353434` | Capital, highlights on leaves | 0.4, 0.66, 0.68, 0.78 | 23.2% | Same | L 0.326, C 0.001, h 17.2 |
| `#818188` | Specular glints | 0.4, 0.66, 0.68, 0.78 | 3.0% | Same | L 0.606, C 0.010, h 286.1 |

Incidental marks: none.

### `door-registrars.jpg`

A varnished timber door with brass-bound glazing and two brass pull handles. Strongly orange in this exposure. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `door-registrars.jpg`; https://commons.wikimedia.org/wiki/File:Door_leading_to_Registrars%27_Chambers,_Old_Supreme_Court_Building,_Singapore_-_20101010-01.JPG

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#e88b48` | Timber stile, lit | 0, 0.1, 0.06, 0.8 | 42.7% | Interior light, varnished surface | L 0.723, C 0.140, h 54.1 |
| `#c55f1d` | Timber stile, mid | 0, 0.1, 0.06, 0.8 | 42.2% | Same | L 0.600, C 0.150, h 48.3 |
| `#f3c4ab` | Timber stile, highlight | 0, 0.1, 0.06, 0.8 | 15.1% | Same | L 0.855, C 0.064, h 49.5 |
| `#b98657` | Brass pull handle, mid | 0.635, 0.6, 0.68, 0.76 | 67.3% | Interior light, aged brass | L 0.660, C 0.089, h 63.0 |
| `#dbc6ae` | Brass pull handle, highlight | 0.635, 0.6, 0.68, 0.76 | 27.3% | Same | L 0.838, C 0.040, h 71.0 |
| `#2b150c` | Handle slot shadow | 0.635, 0.6, 0.68, 0.76 | 5.5% | Same | L 0.225, C 0.040, h 42.7 |

Incidental marks: a brass sign reading REGISTRARS' CHAMBERS NOS. 1-8, a PULL label, a printed notice and a keypad lock. All sit outside both boxes (the handle box starts left of the PULL label). The stile box is a strip on the left edge, 6% wide.

### `court1-judges-seat.jpg`

The judge's seat of Court No 1 under a coffered plaster dome, with red leather chairs. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `court1-judges-seat.jpg`; https://commons.wikimedia.org/wiki/File:Judge%27s_seat,_Court_Number_1,_Old_Supreme_Court_Building,_Singapore_-_20101010-01.JPG

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#592a0d` | Panelling, lit panel | 0.17, 0.36, 0.37, 0.55 | 52.6% | Interior light | L 0.344, C 0.080, h 48.7 |
| `#371404` | Panelling, shaded | 0.17, 0.36, 0.37, 0.55 | 46.3% | Same | L 0.243, C 0.062, h 44.1 |
| `#d3c297` | Brass or highlight flecks | 0.17, 0.36, 0.37, 0.55 | 1.1% | Same | L 0.818, C 0.060, h 89.0 |
| `#641615` | Chair leather, shade | 0.43, 0.69, 0.67, 0.8 | 52.0% | Same | L 0.335, C 0.111, h 26.1 |
| `#721e1e` | Chair leather, lit | 0.43, 0.69, 0.67, 0.8 | 42.3% | Same | L 0.372, C 0.118, h 24.9 |
| `#3d180a` | Chair, dark seam | 0.43, 0.69, 0.67, 0.8 | 5.7% | Same | L 0.262, C 0.063, h 40.5 |

Incidental marks: none seen in frame. The panelling box starts left of the chair.

### `court-of-appeal-public-gallery.jpg`

The upper gallery under the coffered timber ceiling, with balusters and tall panelling. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `court-of-appeal-public-gallery.jpg`; https://commons.wikimedia.org/wiki/File:Public_gallery,_Court_of_Appeal_courtroom,_Old_Supreme_Court_Building,_Singapore_-_20101010.jpg

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#34180e` | Dark panelling | 0.67, 0.86, 0.98, 0.99 | 42.4% | Interior, shaded | L 0.247, C 0.048, h 40.2 |
| `#4b2c25` | Dark panelling, reddish | 0.67, 0.86, 0.98, 0.99 | 39.1% | Same | L 0.330, C 0.048, h 33.4 |
| `#60433e` | Panelling edge light | 0.67, 0.86, 0.98, 0.99 | 18.5% | Same | L 0.414, C 0.041, h 29.9 |
| `#442414` | Coffered ceiling, shade | 0.45, 0.03, 0.8, 0.28 | 75.7% | Interior, downlights | L 0.299, C 0.055, h 46.4 |
| `#7b380f` | Coffered ceiling, lit | 0.45, 0.03, 0.8, 0.28 | 23.1% | Same | L 0.424, C 0.106, h 47.3 |
| `#e5eeed` | Downlight | 0.45, 0.03, 0.8, 0.28 | 1.2% | Same | L 0.942, C 0.010, h 189.1 |

Incidental marks: a wall camera and speaker, both outside the boxes. The ceiling box takes in one recessed light (1.2% of the crop), which is the third cluster.

### `court-of-appeal-tables.jpg`

Lawyers' tables with green baize, timber chairs with oxblood leather backs and a mauve carpet. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `court-of-appeal-tables.jpg`; https://commons.wikimedia.org/wiki/File:Lawyers%27_tables,_Court_of_Appeal_courtroom,_Old_Supreme_Court_Building,_Singapore_-_20101010.jpg

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#79dfd7` | Baize top | 0.14, 0.47, 0.46, 0.56 | 81.0% | Interior light | L 0.840, C 0.097, h 188.9 |
| `#bfa194` | Table edge, pale timber | 0.14, 0.47, 0.46, 0.56 | 11.9% | Same | L 0.732, C 0.040, h 44.8 |
| `#3c1f18` | Table edge, shadow | 0.14, 0.47, 0.46, 0.56 | 7.2% | Same | L 0.277, C 0.047, h 34.5 |
| `#9f4f74` | Carpet | 0, 0.57, 0.06, 0.68 | 41.8% | Interior, even | L 0.537, C 0.114, h 352.6 |
| `#97486d` | Carpet, second tone | 0, 0.57, 0.06, 0.68 | 41.8% | Same | L 0.512, C 0.114, h 352.5 |
| `#946284` | Carpet, lilac patch | 0, 0.57, 0.06, 0.68 | 16.4% | Same | L 0.561, C 0.080, h 339.3 |
| `#480f16` | Chair leather, shade | 0.52, 0.62, 0.61, 0.88 | 56.4% | Interior light | L 0.272, C 0.086, h 18.2 |
| `#5c1720` | Chair leather, lit | 0.52, 0.62, 0.61, 0.88 | 42.8% | Same | L 0.323, C 0.100, h 17.5 |
| `#876d63` | Stud highlights | 0.52, 0.62, 0.61, 0.88 | 0.8% | Same | L 0.557, C 0.037, h 42.1 |

Incidental marks: white objects on the tables (microphone shapes, not identified) and no people. None is in a crop. The baize reads cyan in the pixels (hue 189), more than green to the eye in the thumbnail, so treat its hue as the camera's.

### `lamp-court-of-appeal.jpg`

A bronze-framed glass ceiling lamp against a near-black ceiling. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `lamp-court-of-appeal.jpg`; https://commons.wikimedia.org/wiki/File:Lamp,_Court_of_Appeal_courtroom,_Old_Supreme_Court_Building,_Singapore_-_20101010.jpg

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#fef9ce` | Lit glass, clipped | 0.42, 0.58, 0.72, 0.7 | 60.7% | Lamp's own light | L 0.975, C 0.056, h 101.9 |
| `#1b0d05` | Bronze frame | 0.42, 0.58, 0.72, 0.7 | 31.1% | Same | L 0.177, C 0.029, h 52.6 |
| `#935c23` | Amber rim | 0.42, 0.58, 0.72, 0.7 | 8.2% | Same | L 0.525, C 0.101, h 62.9 |
| `#7a481d` | Shade inner face | 0.33, 0.52, 0.5, 0.6 | 49.4% | Lamp's own light | L 0.452, C 0.089, h 58.1 |
| `#1b0e05` | Bronze frame | 0.33, 0.52, 0.5, 0.6 | 36.2% | Same | L 0.179, C 0.029, h 57.2 |
| `#fae7c4` | Lit glass | 0.33, 0.52, 0.5, 0.6 | 14.3% | Same | L 0.934, C 0.050, h 82.8 |

Incidental marks: none. The lit glass is at the sensor's limit, so its hue (102) is a weak reading.

### `rubber-tiles.jpg`

The second-storey floor: grey patterned tiles with a red inlay band. Commons files it as rubber tiles; the pixels read as a patterned floor. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `rubber-tiles.jpg`; https://commons.wikimedia.org/wiki/File:Rubber_tiles_on_the_second_storey,_Old_Supreme_Court_Building,_Singapore_-_20101010.JPG

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#4f504f` | Floor tile, dark | 0.05, 0.8, 0.4, 0.98 | 48.1% | Interior, even | L 0.430, C 0.002, h 145.5 |
| `#5b5d5b` | Floor tile, mid | 0.05, 0.8, 0.4, 0.98 | 42.4% | Same | L 0.476, C 0.004, h 145.5 |
| `#81847b` | Floor tile, pale vein | 0.05, 0.8, 0.4, 0.98 | 9.5% | Same | L 0.608, C 0.014, h 121.9 |

Incidental marks: a red carpet and a white cart at the top, outside the box. The box is the lower left corner, plain grey.

### `strongroom.jpg`

Strongroom No 1: an olive steel door with a dark frame in a cream-painted wall, in hard indoor light. Jacklee, CC BY-SA 3.0. Citation: SOURCES row `strongroom.jpg`; https://commons.wikimedia.org/wiki/File:Strongroom_no_1_of_the_Old_Supreme_Court_Building,_Singapore_-_20080801-01.JPG

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#39432a` | Steel door leaf | 0.62, 0.66, 0.8, 0.84 | 48.1% | Interior, hard light | L 0.366, C 0.043, h 126.1 |
| `#414a36` | Steel door leaf, lit | 0.62, 0.66, 0.8, 0.84 | 30.1% | Same | L 0.395, C 0.035, h 127.6 |
| `#323d1c` | Steel door leaf, dark | 0.62, 0.66, 0.8, 0.84 | 21.8% | Same | L 0.341, C 0.055, h 124.4 |
| `#f0f8dc` | Painted wall | 0.28, 0.5, 0.4, 0.85 | 42.5% | Interior, hard light, green-yellow cast | L 0.966, C 0.038, h 120.1 |
| `#e9f2d6` | Painted wall, mid | 0.28, 0.5, 0.4, 0.85 | 34.3% | Same | L 0.947, C 0.038, h 121.6 |
| `#ddecce` | Painted wall, shaded | 0.28, 0.5, 0.4, 0.85 | 23.2% | Same | L 0.924, C 0.043, h 129.0 |

Incidental marks: a paper number label, a green seal-like disc, tape scraps, two electrical sockets and a door knob. The steel box starts below the knob and the disc, and the wall box is clear of the sockets. The wall may be cream in life; here it reads green-yellow, so the wall hex is a colour-cast reading.

### `allegory-of-justice.jpg`

The pediment relief above the portico, with the dome behind. Plain cornice stone only: the box is the smooth band below the figures. At 473 x 774 px the box is 189 x 35 px. Scott Anderson, CC BY-SA 2.0. Citation: SOURCES row `allegory-of-justice.jpg`; https://commons.wikimedia.org/wiki/File:Allegory_of_Justice,_Old_Supreme_Court_Building,_Singapore_-_20070717.jpg

| Hex | What | Crop (l, t, r, b) | Share | Lighting | OKLCH |
|---|---|---|---|---|---|
| `#c8c4bd` | Cornice stone, lit | 0.05, 0.7, 0.45, 0.745 | 59.4% | Overcast | L 0.822, C 0.011, h 81.8 |
| `#99948b` | Cornice stone, mid | 0.05, 0.7, 0.45, 0.745 | 23.7% | Same | L 0.668, C 0.014, h 82.4 |
| `#6d675d` | Cornice stone, shadow line | 0.05, 0.7, 0.45, 0.745 | 16.9% | Same | L 0.516, C 0.017, h 80.7 |

Incidental marks: the relief figures (Justice with scales, a figure group) fill the band above the box, and a white pole stands in front of the drum. Neither was cropped.

## Fetched, sampled and not kept

Photos fetched and sampled whose files were then removed to hold the set at twelve. The crops were taken on the full-size copies of those files; the boxes are fractions, so the values cannot be re-run from this repo.

| Hex | What | Photo | Crop (l, t, r, b) | Share |
|---|---|---|---|---|
| `#909191` | Rotunda library column, shade | `Old Supreme Court Library ... 20101010-01.JPG` | 0.12, 0.78, 0.25, 0.99 | 42.3% |
| `#8b897e` | Rotunda library dome plaster | same | 0.20, 0.00, 0.70, 0.14 | 38.8% |
| `#784512` | Court No 1 coffered ceiling, timber | `Ceiling of Court Number 1 ... 20101010.JPG` | 0.50, 0.05, 0.90, 0.40 | 48.6% |
| `#724234` | Court of Appeal door timber (glare in the crop; third cluster `#dadde8` is specular) | `Door, Court of Appeal courtroom ... 20101010.jpg` | 0.30, 0.30, 0.52, 0.60 | 52.6% |
| `#431f12` | Court of Appeal door, dark timber behind the handle | same | 0.20, 0.79, 0.34, 0.85 | 61.4% |
| `#ded6c0` | Dome drum cornice stone (crop took cornice shadow, third cluster `#272219` at 22.9%) | `dome.jpg` | 0.34, 0.62, 0.50, 0.655 | 45.1% |
| `#6d7879` | Facade column shaft, cool cast | `Columns on the facade ... 20080801.JPG` | 0.72, 0.20, 0.86, 0.58 | 46.5% |

The Rotunda library gave only neutral greys, and the Court No 1 ceiling repeats the golden timber of the Court of Appeal ceiling, so neither adds a colour family.

## Banner pairs

Each pair keeps the sample's OKLCH hue and moves lightness and chroma. Lightness is solved so the WCAG 2 contrast ratio meets the target; chroma is the sample's, or raised to 0.10 where the sample is paler (rows marked C 0.10), and is cut only as far as sRGB needs. Targets: main 5.45:1 on `#ffffff` and 6.69:1 on `#0d1117`; second tone 2.25:1 on `#ffffff` and 11.77:1 on `#0d1117`. Ratios are computed with the WCAG relative-luminance formula on the 8-bit hex shown, so they differ from the targets by up to about 0.06 through rounding. The sampled hex is the family's representative cluster, named in the first column.

| Family (sample) | Variant | Hue | Main light | Ratio | Main dark | Ratio | Second light | Ratio | Second dark | Ratio |
|---|---|---|---|---|---|---|---|---|---|---|
| patina green `#bce0d7` | keep C | 178.5 | `#4f7069` | 5.45 | `#7ea198` | 6.70 | `#92b4ac` | 2.25 | `#b0d3cb` | 11.74 |
| patina green `#bce0d7` | C 0.10 | 178.5 | `#087767` | 5.46 | `#42aa96` | 6.69 | `#58bea9` | 2.25 | `#79dec8` | 11.80 |
| stone grey `#bdbbb3` | keep C | 95.2 | `#6b6962` | 5.49 | `#9b9992` | 6.64 | `#afada5` | 2.25 | `#ceccc4` | 11.77 |
| stone grey `#bdbbb3` | C 0.10 | 95.2 | `#7c6814` | 5.46 | `#ac994c` | 6.68 | `#c0ac60` | 2.26 | `#e0cc7e` | 11.81 |
| door timber orange `#c55f1d` | keep C | 48.3 | `#ad4d04` | 5.47 | `#e77d41` | 6.68 | `#fd9156` | 2.24 | `#febe9c` | 11.77 |
| dark timber `#592a0d` | keep C | 48.7 | `#925d41` | 5.43 | `#c58e70` | 6.74 | `#daa083` | 2.25 | `#fbbfa1` | 11.78 |
| dark timber `#592a0d` | C 0.10 | 48.7 | `#9a5934` | 5.45 | `#cf8a64` | 6.73 | `#e49d77` | 2.24 | `#febe9c` | 11.77 |
| oxblood leather `#5c1720` | keep C | 17.5 | `#9f5358` | 5.45 | `#d48387` | 6.66 | `#e99799` | 2.25 | `#febbbd` | 11.77 |
| oxblood leather `#5c1720` | C 0.10 | 17.5 | `#9f5358` | 5.45 | `#d48387` | 6.66 | `#e99799` | 2.25 | `#febbbd` | 11.77 |
| carpet mauve `#9f4f74` | keep C | 352.6 | `#a04f74` | 5.43 | `#d580a5` | 6.72 | `#ea93b8` | 2.24 | `#feb8d5` | 11.74 |
| lamp glass cream `#fef9ce` | keep C | 101.9 | `#6f6b44` | 5.44 | `#9f9b73` | 6.68 | `#b3af86` | 2.24 | `#d2cea4` | 11.81 |
| lamp glass cream `#fef9ce` | C 0.10 | 101.9 | `#756b17` | 5.42 | `#a69c4e` | 6.75 | `#b9af61` | 2.24 | `#d9ce80` | 11.80 |
| strongroom olive `#39432a` | keep C | 126.1 | `#626e53` | 5.42 | `#929e81` | 6.70 | `#a5b294` | 2.24 | `#c4d0b3` | 11.73 |
| strongroom olive `#39432a` | C 0.10 | 126.1 | `#59722c` | 5.43 | `#88a35d` | 6.71 | `#9bb670` | 2.25 | `#b9d68e` | 11.78 |
| baize cyan `#79dfd7` | keep C | 188.9 | `#017771` | 5.41 | `#3fa9a2` | 6.68 | `#55bdb5` | 2.25 | `#76ddd5` | 11.78 |
| baize cyan `#79dfd7` | C 0.10 | 188.9 | `#047671` | 5.48 | `#39a9a2` | 6.64 | `#51beb6` | 2.24 | `#73ddd5` | 11.74 |
| door brass `#b98657` | keep C | 63.0 | `#905f30` | 5.43 | `#c38f60` | 6.69 | `#d7a373` | 2.24 | `#f8c291` | 11.82 |
| door brass `#b98657` | C 0.10 | 63.0 | `#945d26` | 5.45 | `#c88d57` | 6.67 | `#dca16a` | 2.25 | `#fdbf88` | 11.70 |
| floor grey `#5b5d5b` | keep C | 145.5 | `#686a68` | 5.45 | `#989a98` | 6.68 | `#abadab` | 2.26 | `#cacdca` | 11.80 |
| floor grey `#5b5d5b` | C 0.10 | 145.5 | `#3d7542` | 5.50 | `#6da770` | 6.68 | `#80ba83` | 2.27 | `#9fdaa1` | 11.73 |
Reading the pairs:

- Teal, patina (`#bce0d7`, hue 178.5): the sample is pale (C 0.040). Kept at that chroma the main tone is a dull grey-teal (`#4f7069`). At C 0.10 it is a clear teal (`#087767`, `#58bea9`) and keeps the dome's identity. Use the C 0.10 row.
- Teal, baize (`#79dfd7`, hue 188.9): clean at both settings, but it is 10 degrees from the patina and its hue is the camera's reading, so it adds no family of its own.
- Stone grey (`#bdbbb3`, hue 95.2, C 0.011) and floor grey (`#5b5d5b`, C 0.004): no usable hue. Kept at their chroma they are neutral greys. Raised to C 0.10 they turn mustard and green, which are not the stone or the floor. Treat both as neutrals, not as hue families.
- Door timber (`#c55f1d`, hue 48.3): holds at every target. The dark-theme second tone is chroma-limited by sRGB (C 0.087, `#febe9c`, a peach).
- Dark timber (`#592a0d`, hue 48.7) and door brass (`#b98657`, hue 63.0): the wood is dark (L 0.34), so main tones at L 0.5 to 0.6 read as clay or tan (`#925d41`, `#905f30`) and the dark-theme second tone as peach (`#fbbfa1`). The identity (dark wood) is lost at these targets. Dark timber and door timber share a hue, so they are one family; brass sits 15 degrees away and is a near-duplicate.
- Oxblood leather (`#5c1720`, hue 17.5): the light main tone is a dusty rose (`#9f5358`) and the dark second tone a pink (`#febbbd`). The deep red is lost. See the party note.
- Carpet mauve (`#9f4f74`, hue 352.6): holds, a clean rose pink. See the party note.
- Lamp glass cream (`#fef9ce`, hue 101.9): goes muddy. At the sample's chroma the main tone is khaki (`#6f6b44`); at C 0.10 it is mustard (`#756b17`). The lamp's glow does not survive a 5.45:1 target.
- Strongroom olive (`#39432a`, hue 126.1, C 0.043): kept at its chroma the main tone is a grey-green (`#626e53`), muddy. At C 0.10 it is moss (`#59722c`), clear but no longer steel.

Distinct colour families by sampled hue: teal (patina, baize), timber and brass (hue 48 to 63), red (hue 17 to 25), rose pink (hue 353), cream-yellow lamp glass (hue 102), olive green (hue 126), plus two neutrals (stone and floor grey). That is six chromatic families from twelve photos, one of them (the cream lamp glass) a weak reading, plus the two neutrals.

## Near a party colour

By the rule in "Party colours to stay clear of":

- Near: oxblood leather (hue 17.5, C 0.100) is 4.8 degrees from the crest-red reference. The Court No 1 chair red `#721e1e` (hue 24.9, C 0.118) is 2.6 degrees from it. Both sit in the PAP, PSP and SDP red range.
- Near, at the edge: carpet mauve (hue 352.6, C 0.114) is 29.7 degrees from the crest red, and door timber (hue 48.3, C 0.150) is 26.0 degrees from it on the orange side. Both pass the 30-degree test and are saturated, so by the rule they are near. Door timber reads orange, not red, in the swatches; that is a judgement, not a measurement. Dark timber (hue 48.7, C 0.08) is at the same hue but only just reaches the chroma bar.
- Not near: patina and baize teal (hue 178.5 and 188.9, 60 or more degrees from the sign-blue reference 249.4), stone, floor and the olive and cream tones. No sampled colour is a blue. The sky cluster `#8da9b7` from the rejected dome box is a light blue near the Workers' Party colour, and was not used.
- A pair that keeps the oxblood hue will pass as red-and-white beside the page's white, the PSP pairing. The teal, olive and timber pairs avoid every party.

## Column count

The pedimented portico on the main block has six columns. The count is from `front-cephoto.jpg`, box 0.33, 0.60, 0.47, 0.74 (a 270-pixel-wide patch, enlarged four times): a coupled pair at each end of the portico and two single columns between them, six capitals under the pediment. The same count holds in `front-2014.jpg`, box 0.62, 0.45, 0.92, 0.95 (enlarged twice), which shows six capitals from an angle with the pediment above.

Confidence: about 90% that the portico has six columns. Both views are at an angle or a distance, and the end pairs hide one column behind another in the oblique view, so the straight-on count is the one relied on. What the photos do not settle: the long side colonnades on either side of the portico. They carry more columns and were not counted. If the mark is to show the whole street front, a count from a straight-on photo of the full colonnade is still needed. The count would be 6 for the portico alone.

## Floor plan

None found. The Commons category tree listed in the brief (the Old Supreme Court Building and its subcategories, and the Supreme Court Wing) holds no plan or layout file. The category `Signs in the Old Supreme Court Building` and `Plaques` were not opened; the first-storey category holds `File:Directory on the first storey, Old Supreme Court Building, Singapore - 20101010.JPG`, which was not opened and is a building directory, not a plan. Three Commons file searches (floor plan, courtroom layout, plan drawing) returned only unrelated scanned books and newspapers. No licence is therefore given.

## Not confirmed

- Flickr-origin licences (`dome.jpg`, `allegory-of-justice.jpg`) rest on the Commons metadata alone.
- The pair ratios use the 8-bit hex; the dark second tones for door timber, dark timber and oxblood are chroma-limited by sRGB, so those pairs keep the hue but not the sample's chroma.
- Hue 102 for the lamp glass and 126 for the strongroom steel are weak: one is clipped, the other is a colour cast.
- The count above is for the portico only.
