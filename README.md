Print-Safe (CMYK Lock) for Inkscape

Validate RGB colors against a chosen CMYK ICC profile, flag out-of-gamut fills/strokes/gradient stops, and generate a CMYK-safe swatch palette for rapid editing.

What’s in this ZIP

printsafe.py — extension engine

printsafe.inx — UI/descriptor

Install_PrintSafe.bat — robust installer (tries to install Pillow + copy ICC profiles; non-blocking)

install_printsafe_copyonly_v2.bat — copy-only installer (just installs the extension files)

icc/ — optional CMYK profiles (FOGRA/GRACoL/etc.)

Windows — choose ONE installer
Option A — Robust installer (recommended)

Double-click Install_PrintSafe.bat.

Copies printsafe.py/.inx to your user extensions (and system folder if permitted).

Attempts to install Pillow into Inkscape’s bundled Python (best-effort; won’t block).

Attempts to copy ICC profiles from this ZIP (root or icc\) into Windows’ color store.

If the Pillow/ICC steps fail, it continues and prints what to do.

Restart Inkscape → Extensions → Print → Print-Safe (CMYK Lock).

If ICC copy failed, just double-click each .icc/.icm file to install it.

Option B — Copy-only installer (minimal)

Double-click install_printsafe_copyonly_v2.bat.

Only copies printsafe.py/.inx to user extensions.

Restart Inkscape → Extensions → Print → Print-Safe (CMYK Lock).

If you later see “No module named PIL/ImageCms”, install Pillow (see “Pillow dependency” below).

Linux install

Install Pillow for your distro:

Debian/Ubuntu: sudo apt install python3-pil

Fedora: sudo dnf install python3-pillow

Arch: sudo pacman -S python-pillow
