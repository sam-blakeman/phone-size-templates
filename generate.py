#!/usr/bin/env python3
"""Render print-at-actual-size phone templates to PDF.

Examples:
  python generate.py iphone-18-pro iphone-18-pro-max            # compare two devices, A4, writes out.pdf
  python generate.py iphone-duo --paper letter -o duo.pdf
  python generate.py --all-sheets                                # rebuild everything in pdf/ from sheets.yaml
  python generate.py --list
  python generate.py --check                                     # validate devices.yaml
"""
import argparse
import math
import os
import sys

import yaml
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
PAPERS = {"a4": A4, "letter": letter}
MARGIN = 8.0          # mm
HEADER = 28.0         # mm reserved at top of every page
FOOTER = 8.0          # mm reserved at bottom
GAP = 6.0             # mm between items
LABEL_PAD = 4.0       # mm below each item for nothing (labels are drawn inside)


def load_yaml(name):
    with open(os.path.join(HERE, name)) as f:
        return yaml.safe_load(f)


def screen_mm(screen):
    """Physical active area in mm from pixels plus either ppi or the full-rectangle diagonal in mm."""
    if screen.get("ppi"):
        scale = 25.4 / screen["ppi"]                       # mm per pixel
    elif screen.get("diagonal_mm"):
        scale = screen["diagonal_mm"] / math.hypot(screen["px_w"], screen["px_h"])
    else:
        sys.exit(f"screen needs ppi or diagonal_mm: {screen}")
    return screen["px_w"] * scale, screen["px_h"] * scale


# ---------------------------------------------------------------- items

def build_items(devices, ids, edges=True):
    """Turn device ids into a flat list of drawable items (bodies and edge strips)."""
    by_id = {d["id"]: d for d in devices}
    items, edge_items = [], []
    for did in ids:
        if did not in by_id:
            sys.exit(f"unknown device id: {did}. Try --list")
        dev = by_id[did]
        for st in dev["states"]:
            label = dev["name"] + (f", {st['name']}" if st.get("name") else "")
            b = st["body"]
            items.append({
                "kind": "body", "w": b["w"], "h": b["h"], "d": b["d"],
                "label": label, "weight": st.get("weight_g"),
                "screen": st.get("screen"), "r": st.get("corner_radius_mm", 8),
                "hinge": st.get("hinge"),
            })
            if edges:
                edge_items.append({"kind": "edge", "w": b["d"], "h": b["h"],
                                   "label": f"{label} edge, {b['d']} mm"})
    return items + edge_items


def layout(items, paper_w, paper_h):
    """First-fit row packing.

    Each item goes into the first existing row (any page) with room for it, so thin edge
    strips fill gaps beside the bodies they belong to. Otherwise a new row is started, and
    a new page when the row would run off the bottom.
    """
    right = paper_w - MARGIN
    pages = []          # list of list of rows; row = {"x", "y_top", "h", "items"}

    def fits(row, it, is_last_row):
        if row["x"] + it["w"] > right:
            return False
        if it["h"] <= row["h"]:
            return True
        return is_last_row and row["y_top"] - it["h"] >= FOOTER

    for it in items:
        if it["w"] > right - MARGIN or it["h"] > paper_h - HEADER - FOOTER:
            sys.exit(f"{it['label']} does not fit on this paper size")
        placed = False
        for rows in pages:
            for i, row in enumerate(rows):
                if fits(row, it, i == len(rows) - 1):
                    row["items"].append(dict(it, x=row["x"]))
                    row["x"] += it["w"] + GAP
                    row["h"] = max(row["h"], it["h"])
                    placed = True
                    break
            if placed:
                break
        if placed:
            continue
        # new row on the last page if there is vertical room, else a new page
        if pages:
            last = pages[-1][-1]
            y_top = last["y_top"] - last["h"] - GAP
        if not pages or y_top - it["h"] < FOOTER:
            pages.append([])
            y_top = paper_h - HEADER
        pages[-1].append({"x": MARGIN + it["w"] + GAP, "y_top": y_top, "h": it["h"],
                          "items": [dict(it, x=MARGIN)]})

    # flatten, bottom-aligning items within each row so bodies share a baseline
    out = []
    for rows in pages:
        page = []
        for row in rows:
            base = row["y_top"] - row["h"]
            for it in row["items"]:
                page.append(dict(it, y=base))
        out.append(page)
    return out


# ---------------------------------------------------------------- drawing

def draw_header(c, paper_w, paper_h, title, page_no, page_count):
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN * mm, (paper_h - 10) * mm, f"{title}, actual size")
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGIN * mm, (paper_h - 14.5) * mm,
                 "PRINT AT 100% / ACTUAL SIZE. Turn off 'fit to page' and 'scale to fit'. "
                 "Check the 100 mm bar with a ruler before cutting.")
    c.drawRightString((paper_w - MARGIN) * mm, (paper_h - 10) * mm, f"page {page_no} of {page_count}")
    x0, y0 = MARGIN * mm, (paper_h - 20) * mm
    c.setLineWidth(0.6)
    c.line(x0, y0, x0 + 100 * mm, y0)
    for i in range(0, 101, 10):
        t = 2.2 * mm if i % 50 == 0 else 1.4 * mm
        c.line(x0 + i * mm, y0, x0 + i * mm, y0 + t)
    c.setFont("Helvetica", 6.5)
    c.drawString(x0, y0 - 3 * mm, "0")
    c.drawString(x0 + 48 * mm, y0 - 3 * mm, "50 mm")
    c.drawString(x0 + 94 * mm, y0 - 3 * mm, "100 mm")
    # 3 inch bar for anyone with an imperial ruler
    xi = x0 + 110 * mm
    c.setLineWidth(0.6)
    c.line(xi, y0, xi + 3 * 25.4 * mm, y0)
    for i in range(0, 4):
        c.line(xi + i * 25.4 * mm, y0, xi + i * 25.4 * mm, y0 + 2.2 * mm)
    c.drawString(xi, y0 - 3 * mm, "0")
    c.drawString(xi + 3 * 25.4 * mm - 4 * mm, y0 - 3 * mm, "3 in")


def draw_footer(c, paper_h):
    c.setFont("Helvetica", 6.5)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawString(MARGIN * mm, 4 * mm,
                 "Shaded area = active display, computed from manufacturer resolution and ppi. "
                 "Corner radii are estimates. Edge strips show thickness only. "
                 "github.com/sam-blakeman/phone-size-templates")
    c.setFillColorRGB(0, 0, 0)


def draw_body(c, it):
    x, y, w, h = it["x"], it["y"], it["w"], it["h"]
    if it.get("screen"):
        sw, sh = screen_mm(it["screen"])
        sx, sy = x + (w - sw) / 2, y + (h - sh) / 2
        c.setLineWidth(0.35)
        c.setStrokeColorRGB(0.5, 0.5, 0.5)
        c.setFillColorRGB(0.93, 0.93, 0.93)
        c.roundRect(sx * mm, sy * mm, sw * mm, sh * mm, max(it["r"] - 2.5, 1) * mm, stroke=1, fill=1)
        c.setFillColorRGB(0.45, 0.45, 0.45)
        c.setFont("Helvetica", 6)
        c.drawCentredString((x + w / 2) * mm, (sy + 3) * mm,
                            f"screen {sw:.1f} x {sh:.1f} mm, bezel {(w - sw) / 2:.1f} side / {(h - sh) / 2:.1f} top")
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)
    c.roundRect(x * mm, y * mm, w * mm, h * mm, it["r"] * mm, stroke=1, fill=0)
    if it.get("hinge"):
        c.setDash(2, 2); c.setStrokeColorRGB(0.5, 0.5, 0.5)
        if it["hinge"] == "vertical":
            c.line((x + w / 2) * mm, y * mm, (x + w / 2) * mm, (y + h) * mm)
        else:
            c.line(x * mm, (y + h / 2) * mm, (x + w) * mm, (y + h / 2) * mm)
        c.setDash(); c.setStrokeColorRGB(0, 0, 0)
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString((x + w / 2) * mm, (y + h / 2 + 2) * mm, it["label"])
    c.setFont("Helvetica", 7)
    wt = f", {it['weight']} g" if it.get("weight") else ""
    c.drawCentredString((x + w / 2) * mm, (y + h / 2 - 3) * mm, f"{w} x {h} x {it['d']} mm{wt}")


def draw_edge(c, it):
    x, y, w, h = it["x"], it["y"], it["w"], it["h"]
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)
    c.roundRect(x * mm, y * mm, w * mm, h * mm, min(w / 2, 2.5) * mm, stroke=1, fill=0)
    c.saveState()
    c.translate((x + w / 2) * mm, (y + h / 2) * mm)
    c.rotate(90)
    c.setFont("Helvetica", 5.5)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(0, -1.5, it["label"])
    c.restoreState()


def render(devices, ids, paper, out, title, edges=True):
    pw_pt, ph_pt = PAPERS[paper]
    items = build_items(devices, ids, edges)
    # try portrait and landscape, keep whichever needs fewer pages (portrait wins ties)
    portrait = layout(items, pw_pt / mm, ph_pt / mm)
    landscape = layout(items, ph_pt / mm, pw_pt / mm)
    if len(landscape) < len(portrait):
        pages, (pw_pt, ph_pt) = landscape, (ph_pt, pw_pt)
    else:
        pages = portrait
    paper_w, paper_h = pw_pt / mm, ph_pt / mm
    c = canvas.Canvas(out, pagesize=(pw_pt, ph_pt), invariant=1)  # deterministic output, no timestamps
    c.setTitle(f"{title}, actual size ({paper.upper()})")
    c.setAuthor("phone-size-templates")
    for n, pg in enumerate(pages, 1):
        draw_header(c, paper_w, paper_h, title, n, len(pages))
        for it in pg:
            (draw_body if it["kind"] == "body" else draw_edge)(c, it)
        draw_footer(c, paper_h)
        c.showPage()
    c.save()
    return len(pages)


# ---------------------------------------------------------------- checks

def check(devices):
    problems = 0
    for d in devices:
        for k in ("id", "name", "maker", "source", "states"):
            if k not in d:
                print(f"ERROR {d.get('id', '?')}: missing {k}"); problems += 1
        for st in d["states"]:
            b = st["body"]
            tag = d["id"] + (f"/{st['name']}" if st.get("name") else "")
            if st.get("screen"):
                sw, sh = screen_mm(st["screen"])
                if sw > b["w"] or sh > b["h"]:
                    print(f"ERROR {tag}: screen {sw:.1f}x{sh:.1f} larger than body {b['w']}x{b['h']}"); problems += 1
                diag = math.hypot(sw, sh) / 25.4
                stated = st["screen"].get("diagonal_in")
                flag = ""
                if stated and abs(diag - stated) > 0.05:
                    flag = f"  WARNING: stated {stated} in"; problems += 1
                print(f"ok  {tag:28s} body {b['w']}x{b['h']}x{b['d']}  screen {sw:.1f}x{sh:.1f} mm  diag {diag:.2f} in{flag}")
            else:
                print(f"ok  {tag:28s} body {b['w']}x{b['h']}x{b['d']}  (no screen data)")
    return problems


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*", help="device ids from devices.yaml")
    ap.add_argument("--paper", choices=PAPERS, default="a4")
    ap.add_argument("-o", "--out", default="out.pdf")
    ap.add_argument("--title", default=None)
    ap.add_argument("--no-edges", action="store_true", help="omit thickness strips")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--all-sheets", action="store_true", help="rebuild pdf/ from sheets.yaml")
    a = ap.parse_args()

    devices = load_yaml("devices.yaml")["devices"]

    if a.list:
        for d in devices:
            states = ", ".join(s.get("name", "single") for s in d["states"])
            print(f"{d['id']:22s} {d['name']:22s} {d['maker']:8s} {d.get('released', '')}  [{states}]")
        return
    if a.check:
        sys.exit(1 if check(devices) else 0)
    if a.all_sheets:
        sheets = load_yaml("sheets.yaml")["sheets"]
        os.makedirs(os.path.join(HERE, "pdf"), exist_ok=True)
        for s in sheets:
            for paper in s["paper"]:
                out = os.path.join(HERE, "pdf", f"{s['id']}-{paper}.pdf")
                n = render(devices, s["devices"], paper, out, s["title"])
                print(f"wrote {os.path.relpath(out, HERE)} ({n} page{'s' if n > 1 else ''})")
        return
    if not a.ids:
        ap.error("give device ids, or --list / --check / --all-sheets")
    by_id = {d["id"]: d for d in devices}
    title = a.title or " and ".join(by_id[i]["name"] for i in a.ids if i in by_id)
    n = render(devices, a.ids, a.paper, a.out, title, edges=not a.no_edges)
    print(f"wrote {a.out} ({n} page{'s' if n > 1 else ''})")


if __name__ == "__main__":
    main()
