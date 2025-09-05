#!/usr/bin/env python3
# Print-Safe (CMYK Lock)
# - Validate fills/strokes + linear/radial gradient stops vs chosen CMYK ICC
# - Generate larger CMYK-safe .gpl palette (tunable)
# - Clear flags (restore prior stroke/width)
# - Works across Pillow builds (no 'intent=' args)

import os, re, traceback
import inkex
from inkex import Color
from PIL import ImageCms, Image

# ---------- logging -----------------------------------------------------------

def _probe_path():
    if os.name == "nt":
        return os.path.join(os.path.expanduser("~"), "printsafe_windows_probe.log")
    return "/tmp/printsafe_probe.log"

def log(msg):
    try:
        from datetime import datetime
        with open(_probe_path(), "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

# ---------- color parsing -----------------------------------------------------

HEX6 = re.compile(r"^#([0-9A-Fa-f]{6})$")
HEX3 = re.compile(r"^#([0-9A-Fa-f]{3})$")
RGBF = re.compile(r"^rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)$")

def parse_rgb(val):
    if not val or val == "none":
        return None
    s = val.strip()
    m = HEX6.match(s)
    if m:
        v = m.group(1)
        return tuple(int(v[i:i+2], 16) for i in (0,2,4))
    m = HEX3.match(s)
    if m:
        v = m.group(1)
        return tuple(int(c*2, 16) for c in v)
    m = RGBF.match(s)
    if m:
        r,g,b = (int(m.group(i)) for i in (1,2,3))
        return (max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b)))
    try:
        c = Color(s)
        if c.is_valid():
            return (c.red, c.green, c.blue)
    except Exception:
        pass
    return None

def rgb_to_hex(rgb): return "#{:02X}{:02X}{:02X}".format(*rgb)
def approx_diff(a,b): return sum((a[i]-b[i])**2 for i in range(3))**0.5

# ---------- robust ImageCms transforms ---------------------------------------

def build_xform(src, dst, in_mode, out_mode):
    for args in (
        (src, dst, in_mode, out_mode, 0, 0),
        (src, dst, in_mode, out_mode, 0),
        (src, dst, in_mode, out_mode),
    ):
        try:
            return ImageCms.buildTransformFromOpenProfiles(*args)
        except TypeError:
            continue
    raise RuntimeError("ImageCms.buildTransformFromOpenProfiles: no compatible signature")

# ---------- palette output ----------------------------------------------------

def ensure_palettes_dir():
    if os.name == "nt":
        base = os.path.join(os.path.expanduser("~"), "AppData","Roaming","Inkscape","palettes")
    else:
        base = os.path.expanduser("~/.config/inkscape/palettes")
    os.makedirs(base, exist_ok=True)
    return base

def make_big_palette(icc_path, name_hint="PrintSafe", density=7, include_gray=True, include_skin=False):
    """
    Build a rounded, printable palette by round-tripping RGB seeds via CMYK.
    density: 3..10 roughly controls hue/steps count (7 = nice middle).
    """
    palettes_dir = ensure_palettes_dir()
    base = os.path.splitext(os.path.basename(icc_path))[0]
    out = os.path.join(palettes_dir, f"{name_hint}_{base}.gpl")

    srgb = ImageCms.createProfile("sRGB")
    cprof = ImageCms.getOpenProfile(icc_path)
    to_cmyk = build_xform(srgb, cprof, "RGB","CMYK")
    to_rgb  = build_xform(cprof, srgb, "CMYK","RGB")

    seeds = []
    if include_gray:
        # 9 greys from 0..248
        for g in (0,32,64,96,128,160,192,224,248):
            seeds.append((g,g,g))

    # color wheel anchors
    wheel = [
        (255,  40,  40), (255, 140,  30), (255, 225,  35),
        ( 60, 200,  50), ( 40, 200, 200), ( 60, 100, 230),
        (170,  70, 200), (230,  50, 120), (255,  40,  40)
    ]
    def lerp(a,b,t): return int(a+(b-a)*t)

    # steps across wheel controlled by density
    hue_steps = max(3, min(12, density))
    light_levels = (0.85, 0.65, 0.45) if density >= 6 else (0.8, 0.6)

    for i in range(len(wheel)-1):
        a, b = wheel[i], wheel[i+1]
        for s in range(hue_steps):
            t = s/float(hue_steps)
            rr,gg,bb = (lerp(a[0],b[0],t), lerp(a[1],b[1],t), lerp(a[2],b[2],t))
            for k in light_levels:
                seeds.append((int(rr*k), int(gg*k), int(bb*k)))

    if include_skin:
        # some common light/med/dark skin-ish seeds
        seeds += [
            (244, 219, 196), (210, 170, 140), (172, 126,  98),
            (130,  89,  66), ( 92,  62,  47)
        ]

    safe = []
    for rgb in seeds:
        im = Image.new("RGB",(1,1), rgb)
        cm = ImageCms.applyTransform(im, to_cmyk)
        rb = ImageCms.applyTransform(cm, to_rgb)
        safe.append(rb.getpixel((0,0)))

    uniq = []
    seen = set()
    for rgb in safe:
        if rgb not in seen:
            uniq.append(rgb); seen.add(rgb)

    with open(out, "w", encoding="utf-8") as f:
        f.write("GIMP Palette\n")
        f.write(f"Name: {name_hint}_{base}\n")
        f.write("# Generated by Print-Safe\n")
        for (r,g,b) in uniq:
            f.write(f"{r:3d} {g:3d} {b:3d}\t{r},{g},{b}\n")
    return out

# ---------- main effect -------------------------------------------------------

MAGENTA = "#FF00FF"
FLAG_ATTR  = "data-printsafe-flag"
OLD_STROKE = "data-ps-oldstroke"
OLD_WIDTH  = "data-ps-oldstrokewidth"

class PrintSafe(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--icc_path", default="")
        pars.add_argument("--flag_width_px", type=int, default=6)
        pars.add_argument("--action", default="validate")  # validate | palette | clear
        # Accept extra palette params (your INX passes these):
        pars.add_argument("--palette_name", default="PrintSafe")
        pars.add_argument("--palette_density", type=int, default=7)
        pars.add_argument("--include_gray", type=inkex.Boolean, default=True)
        pars.add_argument("--include_skin", type=inkex.Boolean, default=False)

    def _msg(self, text):
        try: self.msg(text)
        except Exception: inkex.utils.debug(text)

    def _build_transforms(self, icc_path):
        srgb = ImageCms.createProfile("sRGB")
        cprof = ImageCms.getOpenProfile(icc_path)
        return (
            build_xform(srgb, cprof, "RGB","CMYK"),
            build_xform(cprof, srgb, "CMYK","RGB"),
        )

    def _roundtrip(self, rgb, to_c, to_r):
        im = Image.new("RGB",(1,1), rgb)
        cm = ImageCms.applyTransform(im, to_c)
        rb = ImageCms.applyTransform(cm, to_r)
        return rb.getpixel((0,0))

    def _check_color(self, rgb, to_c, to_r, threshold=20.0):
        back = self._roundtrip(rgb, to_c, to_r)
        return approx_diff(rgb, back) > threshold, back

    def _iter_gradient_stops(self, grad):
        for stop in grad.iterchildren(tag=inkex.addNS('stop','svg')):
            val = stop.get('stop-color')
            if not val:
                st = stop.get('style')
                if st:
                    for part in st.split(';'):
                        if part.strip().startswith('stop-color:'):
                            val = part.split(':',1)[1].strip()
                            break
            rgb = parse_rgb(val) if val else None
            if rgb: yield rgb

    def _resolve_paint(self, val):
        if not val or val == "none": return []
        s = val.strip()
        # paint server?
        if s.startswith("url(") and "#" in s:
            gid = s[s.find("#")+1 : s.rfind(")")]
            grad = self.svg.getElementById(gid)
            if grad is None:
                try: grad = self.svg.xpath(f'//*[@id="{gid}"]')[0]
                except Exception: grad = None
            return list(self._iter_gradient_stops(grad)) if grad is not None else []
        # solid
        rgb = parse_rgb(s)
        return [rgb] if rgb else []

    def _flag_element(self, elem, width_px):
        st = elem.style or inkex.Style()
        if elem.get(FLAG_ATTR) != "1":
            if "stroke" in st:       elem.set(OLD_STROKE, st["stroke"])
            if "stroke-width" in st: elem.set(OLD_WIDTH, st["stroke-width"])
        st["stroke"] = MAGENTA
        st["stroke-width"] = f"{max(1,int(width_px))}px"
        elem.style = st
        elem.set(FLAG_ATTR, "1")

    def _clear_flags(self):
        count = 0
        for elem in self.svg.iter():
            if elem.get(FLAG_ATTR) == "1":
                st = elem.style or inkex.Style()
                old_s = elem.get(OLD_STROKE)
                old_w = elem.get(OLD_WIDTH)
                if old_s is not None: st["stroke"] = old_s
                elif st.get("stroke") == MAGENTA: st.pop("stroke", None)
                if old_w is not None: st["stroke-width"] = old_w
                elif st.get("stroke-width"): st.pop("stroke-width", None)
                elem.style = st
                for a in (FLAG_ATTR, OLD_STROKE, OLD_WIDTH):
                    if a in elem.attrib: del elem.attrib[a]
                count += 1
        self._msg(f"Cleared flags on {count} object(s).")
        log(f"clear: {count}")

    def effect(self):
        log("Print-Safe start")

        action = (self.options.action or "validate").strip()
        if action == "clear":
            self._clear_flags()
            return

        icc = (self.options.icc_path or "").strip()
        if not icc or not os.path.isfile(icc):
            self._msg("Choose a valid CMYK ICC (.icc/.icm). On Windows: C:\\Windows\\System32\\spool\\drivers\\color")
            log("abort: bad ICC: ''")
            return

        if action == "palette":
            try:
                p = make_big_palette(
                    icc_path=icc,
                    name_hint=(self.options.palette_name or "PrintSafe"),
                    density=max(3, min(10, int(self.options.palette_density or 7))),
                    include_gray=bool(self.options.include_gray),
                    include_skin=bool(self.options.include_skin),
                )
                self._msg(f"Palette written:\n{p}\n(Load via View → Swatches.)")
                log(f"palette OK: {p}")
            except Exception as e:
                self._msg(f"Palette generation failed:\n{e}")
                log(f"palette FAIL: {repr(e)}")
            return

        # validate
        try:
            to_c, to_r = self._build_transforms(icc)
            log("transform build OK")
        except Exception as e:
            self._msg(f"Failed to use ICC profile:\n{e}")
            log(f"transform build FAIL: {repr(e)}")
            return

        bad_count = 0
        flagged = set()
        width_px = max(1, int(self.options.flag_width_px or 6))
        sample_thresh = 20.0

        for elem in self.svg.iter():
            st = elem.style
            if not st: continue

            for key in ("fill", "stroke"):
                val = st.get(key)
                if not val: continue
                colors = self._resolve_paint(val)
                if not colors: continue

                out = False; before = after = None
                for rgb in colors:
                    bad, back = self._check_color(rgb, to_c, to_r, sample_thresh)
                    if bad:
                        out = True
                        if before is None:
                            before, after = rgb, back
                        break
                if out:
                    if elem not in flagged:
                        self._flag_element(elem, width_px)
                        flagged.add(elem); bad_count += 1
                    break

        if bad_count:
            if bad_count == 1 and before and after:
                self._msg(f"Found 1 object out of gamut. Marked with magenta outline "
                          f"(e.g. {rgb_to_hex(before)} → {rgb_to_hex(after)}).")
            else:
                self._msg(f"Found {bad_count} object(s) with out-of-gamut colors. Marked with magenta outline.")
            log(f"validate: flagged {bad_count}")
        else:
            self._msg("All sampled colors (incl. gradient stops) appear within gamut for this ICC.")
            log("validate: none")

# ---------- entry -------------------------------------------------------------

if __name__ == "__main__":
    try:
        PrintSafe().run()
    except Exception as e:
        try:
            with open(_probe_path(), "a", encoding="utf-8") as f:
                f.write("fatal: " + repr(e) + "\n" + traceback.format_exc() + "\n")
        except Exception:
            pass
        raise
