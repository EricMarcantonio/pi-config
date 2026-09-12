# woodbuild/spec_from_freecad.py
"""FreeCAD document -> build spec.  The ONLY module that imports FreeCAD.

The model supplies the envelope, the door opening and the band; the framing,
build-up and roof structure are locked decisions from the design document.
"""

import json
import os
import sys

from .spec import BuildSpec, SpecError

# locked build decisions (design doc, "Reference -> wood translation")
WALL_LAYERS = ["smartside_grooved", "osb_7_16", "2x4"]
MODEL_ROOF_T = 80.0                        # the resin roof's own thickness in KeterPent97.FCStd
ROOF_BUILD_UP = 89.0 + 11.0 + 20.0        # 2x4 rafter + OSB deck + steel
FLOOR_BUILD_UP = 89.0 + 89.0 + 18.0       # skid + joist + deck
STORE = "7011"
PROVINCE = "ON"

def _wall_bounds(doc):
    """Bounds of the wall envelope: WallsOpen when present, else the panels+posts."""
    import FreeCAD
    walls = doc.getObject("WallsOpen")
    if walls is not None:
        return walls.Shape.BoundBox
    xs, ys, zs = [], [], []
    for o in doc.Objects:
        name = o.Name
        if not (name.endswith(("Cut", "CutL", "CutR")) or name.startswith("Post")):
            continue
        if not getattr(o, "Shape", None) or o.Shape.isNull():
            continue
        bb = o.Shape.BoundBox
        xs += [bb.XMin, bb.XMax]; ys += [bb.YMin, bb.YMax]; zs += [bb.ZMin, bb.ZMax]
    if not xs:
        raise SpecError("model has neither WallsOpen nor wall panels")
    return FreeCAD.BoundBox(min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))


def envelope_from_shape_bounds(xmin, xmax, ymin, ymax, zmax_wall,
                               model_roof_t, roof_fall):
    """Build the envelope from the model's wall bounds.

    In the model the wall top IS the roof underside, so the product's overall
    height is that z plus the MODEL's own roof thickness (80 mm). The wood roof
    build-up (120 mm) is a spec decision and must not enter the envelope.
    """
    return {"width": round(xmax - xmin, 2), "depth": round(ymax - ymin, 2),
            "height_tall": round(zmax_wall + model_roof_t, 2),
            "roof_fall": float(roof_fall), "tall_side": "front"}


def envelope_from_bounds_list(bounds, model_roof_t, roof_fall):
    """Pure helper: [[xmin,xmax,ymin,ymax,zmax_wall], ...] -> envelope dict."""
    xmin = min(b[0] for b in bounds); xmax = max(b[1] for b in bounds)
    ymin = min(b[2] for b in bounds); ymax = max(b[3] for b in bounds)
    zmax = max(b[4] for b in bounds)
    return envelope_from_shape_bounds(xmin, xmax, ymin, ymax, zmax, model_roof_t, roof_fall)


def band_opening(model_band, envelope_width, corner_width, height_tall,
                 roof_build_up, door_head):
    """Re-place the clerestory band for the wood roof build-up and corners.

    The model's band spans between 45 mm moulded posts and sits under an 80 mm
    resin roof. Wood corners are 89 mm and the wood roof build-up is 120 mm, so
    the band both narrows (2698.92 -> 2610.92) and drops 40 mm. Dropping it keeps
    the 300 mm band under an unchanged envelope while staying above the door head.
    """
    band_w, band_h, _model_sill = model_band
    wall_top = height_tall - roof_build_up
    sill = round(wall_top - band_h, 2)
    if sill < door_head:
        raise SpecError("band does not fit: sill %.2f mm is below the door head %.2f mm"
                        % (sill, door_head))
    return {"wall": "front", "kind": "band",
            "width": round(envelope_width - 2 * corner_width, 2),
            "height": float(band_h), "sill": sill, "header": None,
            "mullions": 4, "panes": [3.5, 1.5, 4.5, 4.5, 1.5]}


def spec_skeleton(envelope):
    return {
        "build": "keter-pent-97-wood",
        "source": {"kind": "product", "sku": "1001865367", "model": "260435",
                   "cad": "~/freecad/KeterPent97.FCStd",
                   "url": "https://www.homedepot.ca/product/1001865367"},
        "envelope": envelope,
        "wall": {"stud": "2x4", "spacing": 406.4, "top_plates": 2,
                 "sole_plate": "pt_2x4", "bearing_plate": True, "corner_width": 89.0,
                 "layers_out_to_in": WALL_LAYERS},
        "roof": {"rafter": "2x4", "spacing": 304.8, "purlin": "mid_span",
                 "deck": "osb_7_16", "covering": "corrugated_steel",
                 "build_up": ROOF_BUILD_UP,
                 "overhang": {"front": 60.0, "back": 40.0, "side": 45.0}},
        "floor": {"joist": "pt_2x4", "spacing": 406.4, "deck": "plywood_tg_18",
                  "skids": "pt_4x4", "build_up": FLOOR_BUILD_UP, "below_datum": True},
        "openings": [],
        "substitutions": [
            {"ref": "40 mm resin double-wall panel", "build": "111 mm framed wall",
             "consequence": "interior clear 2566.9 x 1957.3 mm, volume ~10.2 m3",
             "changes_diagram": False},
            {"ref": "clerestory band 2698.92 mm between 45 mm moulded posts",
             "build": "band 2610.92 mm between 89 mm corners, dropped 40 mm",
             "consequence": "sill strip above the doors shrinks 67 mm to 27 mm",
             "changes_diagram": True},
            {"ref": "45 x 45 mm moulded corner post", "build": "3-stud 2x4 corner, 89 x 140",
             "consequence": "corner trim detail required", "changes_diagram": True},
            {"ref": "triangular louvre vent 620 x 300", "build": "12 x 18 in rectangular louvre",
             "consequence": "triangular filler panel needed, rough opening changed",
             "changes_diagram": True},
            {"ref": "resin floor + 60 mm plinth", "build": "PT joists + T&G deck",
             "consequence": "196 mm of structure below the datum; base must be excavated/levelled",
             "changes_diagram": True},
            {"ref": "resin/steel sandwich roof (80 mm)", "build": "2x4 rafters + purlin + OSB + steel (120 mm)",
             "consequence": "keeps the 300 mm clerestory band under the fixed envelope",
             "changes_diagram": True},
            {"ref": "moulded resin door leaves", "build": "framed 18 mm plywood leaves",
             "consequence": "hinges and hasp must suit outward-swinging doors",
             "changes_diagram": True},
            {"ref": "level ground only", "build": "compacted gravel/pavers + skids",
             "consequence": "new requirement the reference does not have",
             "changes_diagram": False},
            {"ref": "145 mm plank grooves", "build": "manufacturer's grooved siding",
             "consequence": "groove pitch differs (cosmetic)", "changes_diagram": False},
        ],
        "pricing": {"store": STORE, "province": PROVINCE, "search": {
            "2x4": "2x4x8 SPF stud", "2x6": "2x6x8 SPF", "2x8": "2x8x8 SPF",
            "pt_2x4": "2x4x8 pressure treated", "pt_4x4": "4x4x8 pressure treated",
            "osb_7_16": "7/16 OSB sheathing", "plywood_tg_18": "3/4 tongue and groove plywood",
            "plywood_ext_18": "3/4 exterior plywood", "smartside_grooved": "LP SmartSide panel siding grooved",
            "polycarbonate_6": "6mm polycarbonate sheet", "louvre_12x18": "12x18 aluminium gable vent",
            "steel_roof": "corrugated steel roofing panel",
            "screws_3in": "3 inch exterior structural screws",
            "nails_8d": "8d galvanised sheathing nails",
            "adhesive": "construction adhesive",
            "sealant": "exterior sealant caulk",
            "hinges": "shed door hinges",
            "hasp": "hasp and staple lock",
            "gravel": "crushed gravel 3/4 inch"}},
        "options": {"kerf": 3.0, "retain_offcut_min": 300.0},
    }


def openings_from_doc(doc, envelope):
    """Read the door and band from the model's own cutter objects.

    The door opening and the transoms keep the model's sizes; the band is
    re-placed for the wood roof build-up and corner width by band_opening().
    """
    door = doc.getObject("fw_door")
    band = doc.getObject("fw_band")
    if door is None or band is None:
        raise SpecError("model is missing fw_door / fw_band cutters")
    dbb = door.Shape.BoundBox
    bbb = band.Shape.BoundBox
    door_w = round(dbb.XLength, 2)
    door_h = round(dbb.ZLength, 2)
    door_head = round(dbb.ZMax, 2)
    band_block = band_opening(model_band=(round(bbb.XLength, 2), round(bbb.ZLength, 2),
                                          round(bbb.ZMin, 2)),
                              envelope_width=envelope["width"],
                              corner_width=89.0,
                              height_tall=envelope["height_tall"],
                              roof_build_up=ROOF_BUILD_UP,
                              door_head=door_head)
    transom_sill = round(door_head - 300.0, 2)
    louvre_sill = round(door_head - 480.0, 2)
    return [
        {"wall": "front", "kind": "door", "width": door_w, "height": door_h,
         "sill": 0.0, "header": "2x8"},
        band_block,
        {"wall": "left", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": transom_sill, "header": None},
        {"wall": "right", "kind": "transom", "width": 595.0, "height": 220.0,
         "sill": transom_sill, "header": None},
        {"wall": "left", "kind": "louvre", "width": 457.0, "height": 305.0,
         "sill": louvre_sill, "header": None, "near": "back_top"},
        {"wall": "right", "kind": "louvre", "width": 457.0, "height": 305.0,
         "sill": louvre_sill, "header": None, "near": "back_top"},
    ]


def spec_from_doc(doc, wall_zmax=None):
    import FreeCAD  # noqa: F401
    bb = _wall_bounds(doc)
    env = envelope_from_shape_bounds(bb.XMin, bb.XMax, bb.YMin, bb.YMax,
                                     wall_zmax if wall_zmax is not None else bb.ZMax,
                                     MODEL_ROOF_T, 200.0)
    spec = spec_skeleton(env)
    spec["openings"] = openings_from_doc(doc, env)
    return spec


def check_envelope(spec, doc):
    """Fail loudly if the model no longer matches the spec."""
    bb = _wall_bounds(doc)
    width = bb.XMax - bb.XMin
    depth = bb.YMax - bb.YMin
    env = spec["envelope"]
    if abs(width - env["width"]) > 1.0 or abs(depth - env["depth"]) > 1.0:
        raise SpecError("envelope mismatch: model is %.1f x %.1f mm, spec says %.1f x %.1f mm"
                        % (width, depth, env["width"], env["depth"]))


def main(doc_path=None, out_path=None):
    import FreeCAD
    doc_path = doc_path or os.path.expanduser("~/freecad/KeterPent97.FCStd")
    out_path = out_path or os.path.expanduser(
        "~/freecad/keter_pent97_build/keter_pent97.spec.json")
    doc = FreeCAD.openDocument(doc_path)
    spec = spec_from_doc(doc)
    BuildSpec(spec).validate()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(spec, fh, indent=2)
    print("wrote %s" % out_path)
    return out_path


if __name__ == "__main__":
    main(*(sys.argv[1:] or []))
