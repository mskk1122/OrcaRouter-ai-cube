# Mechanical delivery report — 2026-09-07

## Delivered

- `cad/enclosure.py`: editable parametric Python CAD with true Manifold Boolean solids; includes reproducible mesh export, geometric validation, and depth-buffer raster rendering.
- `cad/requirements.txt`, `cad/.gitignore`: pinned core CAD dependencies; locally installed `cad/vendor/` excluded from source control.
- `cad/stl/shell.stl`: 149,784-byte binary STL; print with exterior top on bed (already oriented).
- `cad/stl/base.stl`: 142,284-byte binary STL; print flat (already oriented).
- `cad/renders/assembly.png`, `exploded.png`, `cutaway.png`, `print-layout.png`: actual CAD mesh renders, 1280 × 1024 pixels; inspected visually. The cutaway and component blocks are reference illustrations, not extra printed parts.
- `cad/validation.json`: generated validation evidence.
- `docs/enclosure.md`: Korean sourcing notes, physical assembly, printing, fasteners, tolerances, routing, and limitations.

No commits, purchases, paid services, or changes outside the assigned CAD/doc ownership were made. CAD libraries required an approved network install and approved local DLL execution because the managed sandbox initially blocked them. Both succeeded; no approval blocker remains.

## Dimensions and design decisions

Kept 82 W × 78 D × 82 H mm. XY corner radius 6 mm, normal wall/top 2 mm, hidden local top membrane 1 mm over a 37 × 37 mm recess. Copper electrode is 35 × 35 mm. Unmarked top remains fully opaque and closed.

Official Waveshare primary product search and PDF confirm PCB **45 × 31 mm**, active **23.4 × 23.4 mm**, PH2.0 connector. Explicitly corrected the unrelated OLED 40.5 × 37.5 mm size. Front window is 25.4 mm square, display centre Z48 mm. LCD is retained at PCB edges by integral guides and nylon ties, without adhesive on the active display.

Adafruit3968 official page confirms 40 mm overall and 20 mm height; current title is 4 ohm 5 W, with a 2024 revision from the older 3 W design. A conservative 40 × 40 × 20 mm box fits the right-side U cradle. Frame foam and two ties behind the magnet retain it; the diaphragm is not clamped.

Pi is vertical at rear, on known 58 × 23 mm M2.5 centres, with PCB Z16–46. The grounded PCB plane lies outside the electrode footprint. USB edge faces upward, with connectors biased left. Reserved USB plug/turn corridor is 38 × 20 × 24 mm, and LCD lead corridor is 8 × 12 × 16 mm. Sensor is upper-left, mic lower-front-left, amp lower centre. Every component has a physical retention feature. Unknown board mounting-hole patterns are deliberately unused.

Base closes with four M3 nylon screws and captive nylon nuts. SD access requires base removal. Rear 20 × 9 mm opening is a generic service/cable opening with separate tie-down strain relief, not a falsely precise port cutout. Power goes to Pi PWR IN; microphone goes through a flexible OTG cable to Pi USB.

## Reproduction and actual checks

```powershell
& 'C:/Users/mskwo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -m pip install --target cad/vendor manifold3d trimesh
& 'C:/Users/mskwo/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' cad/enclosure.py
```

Final CAD command exited 0. It exports STL, reloads the files in trimesh, validates watertightness and winding, checks positive volume, and counts connected vertex components. It also evaluates actual Boolean intersections in assembly coordinates.

| Check | Shell | Base |
|---|---:|---:|
| Watertight | true | true |
| Consistent winding | true | true |
| Connected bodies | 1 | 1 |
| Volume mm³ | 66,473.29 | 26,121.65 |
| Triangles | 2,994 | 2,844 |
| Print bounds mm | 82 × 78 × 78.8 | 82 × 78 × 49 |

Shell/base intersection is numerical zero (5.33e−15 mm³). All seven reference component envelopes have zero intersection with printed material and one another. Both reserved cable corridors have zero intersection with printed material and reference component envelopes. These checks concern envelopes, not full supplier CAD models or routed cable simulations.

Visual verification opened all four PNGs. An initial painter-order preview artifact was corrected by implementing per-pixel depth buffering; final exterior correctly shows the unmarked solid top, LCD aperture, mic grille, side speaker grille, and removable base. No floating CAD islands were accepted.

## Remaining physical checks

This is prototype CAD requiring dry fit, not a manufacturing-qualified enclosure. Confirm display glass thickness and active-area centring, PCB-edge areas safe to clamp, PH2.0 direction, USB plug dimensions/turn radius, speaker revision/frame profile, foam thickness, and tie paths using purchased parts. Pi model is a board envelope rather than every mounted component. Confirm available clearance for headers and the actual microphone USB connection. Support generation, slicer review, fit coupons, tapping/reaming pilot holes, heat/acoustic/RF testing, and capacitive sensitivity calibration remain physical production steps. Internal ledges and the base frame require removable print supports.

Sources: [Waveshare LCD manual](https://files.waveshare.com/upload/7/70/1.3inch_LCD_Module_user_manual_en.pdf), [Waveshare product](https://www.waveshare.com/catalog/product/view/id/3637/s/1.3inch-lcd-module/category/356/), [Adafruit3968](https://www.adafruit.com/product/3968). The Waveshare direct open returned 403, but its official indexed product result and official PDF independently agreed on dimensions.
