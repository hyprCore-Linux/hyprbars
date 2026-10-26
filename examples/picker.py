#!/usr/bin/env python3
"""hyprbars bar_image tester: click a PNG to apply live (hyprctl keyword, no reload)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, GLib, Gtk, Pango

BDIR = Path(__file__).resolve().parent
TITLEBARS = BDIR / "titlebars"
SHARE = Path.home() / ".local/share/neuronix/hyprbars"
HYPR_CONF = Path.home() / ".config/hypr/hyprland.conf"
THUMB = 96


def pngs() -> list[Path]:
    """Synthetic tiles in examples/ plus extracted frame titlebars (tiles first)."""
    found: list[Path] = []
    if TITLEBARS.is_dir():
        # Prefer seamless *-tile.png, then banners/plaques.
        found.extend(sorted(TITLEBARS.glob("*-tile.png"), key=lambda p: p.name.lower()))
        found.extend(sorted(TITLEBARS.glob("*-banner.png"), key=lambda p: p.name.lower()))
        found.extend(sorted(TITLEBARS.glob("*-plaque.png"), key=lambda p: p.name.lower()))
    found.extend(sorted(BDIR.glob("*.png"), key=lambda p: p.name.lower()))
    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _hypr_env() -> dict[str, str]:
    env = os.environ.copy()
    if "HYPRLAND_INSTANCE_SIGNATURE" in env:
        return env
    runtime = Path(env.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "hypr"
    if runtime.is_dir():
        for child in sorted(runtime.iterdir()):
            if child.is_dir():
                env["HYPRLAND_INSTANCE_SIGNATURE"] = child.name
                break
    return env


def hyprctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["hyprctl", *args],
        env=_hypr_env(),
        capture_output=True,
        text=True,
        check=False,
    )


def _replace_or_insert_assign(text: str, key: str, value: str) -> str:
    """Update `key = …` inside the hyprbars plugin block when present."""
    pat = re.compile(
        rf"^([ \t]*){re.escape(key)}[ \t]*=[ \t]*.*$",
        re.MULTILINE,
    )
    if pat.search(text):
        return pat.sub(rf"\1{key} = {value}", text, count=1)
    # Insert after bar_gradient or bar_color if no existing key.
    for anchor in ("bar_gradient", "bar_color2", "bar_color"):
        ap = re.compile(
            rf"^([ \t]*){anchor}[ \t]*=[ \t]*.*$",
            re.MULTILINE,
        )
        m = ap.search(text)
        if m:
            indent = m.group(1)
            return (
                text[: m.end()]
                + f"\n{indent}{key} = {value}"
                + text[m.end() :]
            )
    return text


def persist_conf(image: str, opacity: float, scale: float) -> None:
    if not HYPR_CONF.is_file():
        return
    try:
        original = HYPR_CONF.read_text(encoding="utf-8")
    except OSError:
        return
    out = original
    out = _replace_or_insert_assign(out, "bar_image", image if image else "")
    out = _replace_or_insert_assign(out, "bar_image_opacity", f"{opacity:.2f}")
    out = _replace_or_insert_assign(out, "bar_image_scale", f"{scale:.2f}")
    if out != original:
        try:
            HYPR_CONF.write_text(out, encoding="utf-8")
        except OSError:
            pass


def apply_image(path: Path | None, opacity: float, scale: float) -> str:
    """Apply live via keyword. path=None clears bar_image."""
    if path is not None:
        SHARE.mkdir(parents=True, exist_ok=True)
        dest = SHARE / path.name
        try:
            if path.resolve() != dest.resolve():
                shutil.copy2(path, dest)
        except OSError as e:
            return f"copy failed: {e}"
        image = str(dest)
    else:
        image = ""

    steps = [
        ("plugin:hyprbars:bar_image", image),
        ("plugin:hyprbars:bar_image_opacity", f"{opacity:.3f}"),
        ("plugin:hyprbars:bar_image_scale", f"{scale:.3f}"),
    ]
    notes: list[str] = []
    for key, val in steps:
        r = hyprctl("keyword", key, val)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "failed").strip()
            return f"hyprctl keyword {key} failed: {err}"
        notes.append((r.stdout or "ok").strip() or "ok")

    persist_conf(image, opacity, scale)
    if path is None:
        return "cleared bar_image (color/gradient only)"
    return f"applied {path.name}  opacity={opacity:.2f}  scale={scale:.2f}"


class BarImagePicker(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="hyprbars — pick a bar_image")
        self.set_default_size(740, 580)
        self.set_border_width(10)
        self.connect("destroy", Gtk.main_quit)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(vbox)

        head = Gtk.Label()
        head.set_markup(
            "<b>hyprbars bar_image test</b> — frame titlebars + synthetic tiles. "
            "Click to apply via <tt>hyprctl keyword</tt> (no reload). "
            "Prefer <tt>*-tile</tt> for seamless repeats."
        )
        head.set_xalign(0)
        vbox.pack_start(head, False, False, 0)

        self.status = Gtk.Label(label="Select a tile…")
        self.status.set_xalign(0)
        self.status.set_ellipsize(Pango.EllipsizeMode.END)
        vbox.pack_start(self.status, False, False, 0)

        # Opacity / scale
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        vbox.pack_start(controls, False, False, 0)

        controls.pack_start(Gtk.Label(label="opacity"), False, False, 0)
        self.opacity = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.0, 1.0, 0.05
        )
        self.opacity.set_value(1.0)
        self.opacity.set_hexpand(True)
        self.opacity.set_size_request(140, -1)
        controls.pack_start(self.opacity, True, True, 0)

        controls.pack_start(Gtk.Label(label="scale"), False, False, 0)
        self.scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.25, 4.0, 0.25
        )
        self.scale.set_value(1.0)
        self.scale.set_hexpand(True)
        self.scale.set_size_request(140, -1)
        controls.pack_start(self.scale, True, True, 0)

        # Live-adjust without changing the PNG
        tweak = Gtk.Button.new_with_label("Apply opacity/scale")
        tweak.connect("clicked", self._reapply_tweaks)
        controls.pack_start(tweak, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        vbox.pack_start(scroll, True, True, 0)

        self.store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str)  # thumb, name, path
        self.view = Gtk.IconView.new_with_model(self.store)
        self.view.set_pixbuf_column(0)
        self.view.set_text_column(1)
        self.view.set_item_width(THUMB + 36)
        self.view.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.view.connect("item-activated", self._on_activated)
        self.view.connect("selection-changed", self._on_selection)
        scroll.add(self.view)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox.pack_start(btn_row, False, False, 0)

        apply_btn = Gtk.Button.new_with_label("Apply selected")
        apply_btn.connect("clicked", lambda *_: self._apply_selected())
        btn_row.pack_start(apply_btn, False, False, 0)

        clear_btn = Gtk.Button.new_with_label("Clear image")
        clear_btn.connect("clicked", self._clear)
        btn_row.pack_start(clear_btn, False, False, 0)

        refresh_btn = Gtk.Button.new_with_label("Refresh list")
        refresh_btn.connect("clicked", lambda *_: self._fill())
        btn_row.pack_start(refresh_btn, False, False, 0)

        gen_btn = Gtk.Button.new_with_label("Regenerate PNGs")
        gen_btn.connect("clicked", self._regen)
        btn_row.pack_start(gen_btn, False, False, 0)

        close_btn = Gtk.Button.new_with_label("Close")
        close_btn.connect("clicked", lambda *_: self.destroy())
        btn_row.pack_end(close_btn, False, False, 0)

        self._current: Path | None = None
        self._fill()
        self._show_live()

    def _show_live(self) -> None:
        r = hyprctl("getoption", "plugin:hyprbars:bar_image")
        line = (r.stdout or "").strip().splitlines()
        cur = ""
        for ln in line:
            if ln.startswith("str:"):
                cur = ln.split(":", 1)[1].strip()
        if cur:
            self.status.set_text(f"Live: {Path(cur).name} — pick another to switch")
        else:
            self.status.set_text(f"{self.store.iter_n_children(None)} tiles in {BDIR}")

    def _fill(self) -> None:
        self.store.clear()
        items = pngs()
        if not items:
            self.status.set_text("No PNGs — run generate_tiles.py")
            return
        for p in items:
            bg = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, True, 8, THUMB, THUMB
            )
            bg.fill(0x2A2A2AFF)
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(p), THUMB - 8, THUMB - 8, True
                )
                # Tile the small PNG across the thumb so patterns read clearly.
                for y in range(0, THUMB, max(1, pb.get_height())):
                    for x in range(0, THUMB, max(1, pb.get_width())):
                        w = min(pb.get_width(), THUMB - x)
                        h = min(pb.get_height(), THUMB - y)
                        if w < 1 or h < 1:
                            continue
                        src = pb
                        if w != pb.get_width() or h != pb.get_height():
                            src = pb.new_subpixbuf(0, 0, w, h)
                        src.composite(
                            bg,
                            x,
                            y,
                            w,
                            h,
                            float(x),
                            float(y),
                            1.0,
                            1.0,
                            GdkPixbuf.InterpType.NEAREST,
                            255,
                        )
            except GLib.Error:
                pass
            self.store.append([bg, p.stem, str(p)])
        self.status.set_text(f"{len(items)} tiles in {BDIR}")

    def _selected_path(self) -> Path | None:
        paths = self.view.get_selected_items()
        if not paths:
            return None
        it = self.store.get_iter(paths[0])
        return Path(self.store.get_value(it, 2))

    def _vals(self) -> tuple[float, float]:
        return float(self.opacity.get_value()), float(self.scale.get_value())

    def _on_selection(self, *_args) -> None:
        p = self._selected_path()
        if p:
            self.status.set_text(f"Selected {p.name} (double-click or Apply)")

    def _on_activated(self, _view, _path) -> None:
        self._apply_selected()

    def _apply_selected(self) -> None:
        p = self._selected_path()
        if not p:
            self.status.set_text("Nothing selected")
            return
        op, sc = self._vals()
        self.status.set_text(f"Applying {p.name}…")
        while Gtk.events_pending():
            Gtk.main_iteration()
        msg = apply_image(p, op, sc)
        self._current = p
        self.status.set_text(msg)

    def _reapply_tweaks(self, *_args) -> None:
        p = self._selected_path() or self._current
        op, sc = self._vals()
        if p is None:
            # Only push opacity/scale keywords
            r1 = hyprctl("keyword", "plugin:hyprbars:bar_image_opacity", f"{op:.3f}")
            r2 = hyprctl("keyword", "plugin:hyprbars:bar_image_scale", f"{sc:.3f}")
            if r1.returncode or r2.returncode:
                self.status.set_text("keyword failed (is hyprbars loaded?)")
                return
            persist_conf("", op, sc)  # don't wipe image path in conf if unknown
            # re-read live image and persist properly
            live = hyprctl("getoption", "plugin:hyprbars:bar_image")
            img = ""
            for ln in (live.stdout or "").splitlines():
                if ln.startswith("str:"):
                    img = ln.split(":", 1)[1].strip()
            if img:
                persist_conf(img, op, sc)
            self.status.set_text(f"opacity={op:.2f} scale={sc:.2f}")
            return
        self.status.set_text(apply_image(p, op, sc))
        self._current = p

    def _clear(self, *_args) -> None:
        op, sc = self._vals()
        self.status.set_text(apply_image(None, op, sc))
        self._current = None

    def _regen(self, *_args) -> None:
        self.status.set_text("Regenerating synthetic + frame titlebars…")
        while Gtk.events_pending():
            Gtk.main_iteration()
        notes: list[str] = []
        for script, label in (
            (BDIR / "generate_tiles.py", "synthetic"),
            (BDIR / "extract_titlebars.py", "titlebars"),
        ):
            if not script.is_file():
                continue
            cmd = [sys.executable, str(script)]
            if script.name == "extract_titlebars.py":
                cmd.append("--share")
            r = subprocess.run(
                cmd,
                cwd=str(BDIR),
                capture_output=True,
                text=True,
            )
            notes.append(
                label if r.returncode == 0 else f"{label} FAIL"
            )
        self._fill()
        self.status.set_text("Regenerated: " + ", ".join(notes) if notes else "nothing to regen")


def main() -> None:
    os.environ.setdefault("GDK_BACKEND", "wayland")
    win = BarImagePicker()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
