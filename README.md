# phone-size-templates

Print-at-actual-size paper templates for phones, so you can cut one out and feel the size before you buy.

Each template shows the body outline at 1:1 scale, the active screen area shaded inside it so you can see the bezels, a thin strip showing thickness, and a 100 mm calibration bar so you can confirm your printer did not scale the page.

All figures come from the manufacturer's own spec pages. Screen areas are computed from the published resolution and pixel density, which is more accurate than working back from a quoted diagonal.

## Download

| Sheet | Devices | A4 | US Letter |
|---|---|---|---|
| iPhone 18 Pro family | iPhone 18 Pro, iPhone 18 Pro Max | [PDF](pdf/iphone-18-pro-family-a4.pdf) | [PDF](pdf/iphone-18-pro-family-letter.pdf) |
| iPhone Duo | closed and open | [PDF](pdf/iphone-duo-a4.pdf) | [PDF](pdf/iphone-duo-letter.pdf) |
| iPhone 2026 lineup | Duo, 18 Pro, 18 Pro Max | [PDF](pdf/iphone-2026-lineup-a4.pdf) | [PDF](pdf/iphone-2026-lineup-letter.pdf) |
| iPhone 17 family | iPhone 17, Air, 17 Pro, 17 Pro Max | [PDF](pdf/iphone-17-family-a4.pdf) | [PDF](pdf/iphone-17-family-letter.pdf) |
| Galaxy Z Fold8 | closed and open | [PDF](pdf/galaxy-z-fold8-a4.pdf) | [PDF](pdf/galaxy-z-fold8-letter.pdf) |
| Galaxy Z Fold8 Ultra | closed and open | [PDF](pdf/galaxy-z-fold8-ultra-a4.pdf) | [PDF](pdf/galaxy-z-fold8-ultra-letter.pdf) |
| Pixel 11 Pro Fold | closed and open | [PDF](pdf/pixel-11-pro-fold-a4.pdf) | [PDF](pdf/pixel-11-pro-fold-letter.pdf) |
| Foldables 2026 | iPhone Duo, Z Fold8, Z Fold8 Ultra, Pixel 11 Pro Fold | [PDF](pdf/foldables-2026-a4.pdf) | [PDF](pdf/foldables-2026-letter.pdf) |

## How to print

1. Open the PDF in a proper PDF viewer (Preview, Acrobat, or your browser).
2. In the print dialog choose **100%** or **Actual size**. Turn off *fit to page*, *scale to fit* and *shrink oversized pages*.
3. Print, then put a ruler on the 100 mm bar at the top of the page. If it does not read 100 mm the printer scaled the page. Fix the setting and print again.
4. Cut along the outer line. Card stock feels closer to a real phone than plain paper.

## Make your own comparison

Any combination of devices from `devices.yaml` can go on one sheet. The generator packs them onto as many pages as needed.

```bash
pip install -r requirements.txt
python generate.py --list
python generate.py iphone-17-pro iphone-18-pro-max --paper letter -o mine.pdf
```

Flags: `--paper a4|letter`, `--no-edges` to drop the thickness strips, `--title` to override the heading.

## Adding a device

Edit `devices.yaml`. Every entry needs the manufacturer spec page as `source`. Body width, height and depth in mm, weight in grams, and the screen as pixels in the same orientation as the body plus either `ppi` (Apple, Google) or the full-rectangle `diagonal_mm` (Samsung). Foldables list one state per configuration and can set `hinge` to draw a fold line and `flat_edge` to square off the corners on the spine side when closed. See the comments at the top of the file.

Then run:

```bash
python generate.py --check
```

This confirms the screen fits inside the body and, if you supplied `diagonal_in`, that the computed diagonal matches what the manufacturer claims. Add the device to a sheet in `sheets.yaml` if it belongs on a pre-built PDF. The GitHub Action rebuilds `pdf/` on push to `main`.

Pull requests for other makers and older models are welcome. Watch the axis order: Apple and Google list width first in some places and height first in others, and Samsung always lists H x W x D.

## Accuracy

- Outer dimensions and screen areas are exact to the published figures.
- Corner radii are estimates. Manufacturers do not publish them.
- Camera cutouts and the Dynamic Island are not drawn, so the shaded area is total display rather than usable area.
- Manufacturers round dimensions to 0.1 mm and printers drift by a few tenths of a millimetre. Do not use these for case making.

## Licence

MIT. Device names belong to their respective owners.
