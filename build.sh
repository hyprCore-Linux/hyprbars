#!/usr/bin/env bash
# Build hyprbars, install libhyprbars.so, and arm it for the next Hyprland login.
# ./build.sh --disable removes the installed plugin and its hyprland.conf line.
# Does not hyprctl plugin load or reload.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SO_NAME="libhyprbars.so"
BUILT="$ROOT/hyprbars.so"
USER_DEST="${HOME}/.local/lib/hyprland/plugins/${SO_NAME}"
SYS_DEST="/usr/local/lib/hyprland/plugins/${SO_NAME}"
CONF="${HOME}/.config/hypr/hyprland.conf"

if [[ "${1:-}" == "--disable" ]]; then
	rm -f "$USER_DEST"
	rm -f "$SYS_DEST" 2>/dev/null || sudo rm -f "$SYS_DEST" 2>/dev/null || true
	if [[ -f "$CONF" ]]; then
		python3 - "$CONF" <<'PY'
from pathlib import Path
import re
import sys
p = Path(sys.argv[1])
t = p.read_text()
t2 = re.sub(r"(?m)^# hyprbars titlebar\. Load after hyprframes\.\n", "", t)
t2 = re.sub(r"(?m)^# Do not hyprctl plugin load / reload while hyprbars is already up\.\n", "", t2)
t2 = re.sub(r"(?m)^[ \t]*plugin = .*/libhyprbars\.so[ \t]*\n", "", t2)
if t2 != t:
    p.write_text(t2)
    print(f"cleaned {p}")
PY
	fi
	echo "hyprbars disabled — next Hyprland start will not load it"
	exit 0
fi

if [[ ! -f "$ROOT/third_party/hyprutils-0.13/hyprutils/memory/SharedPtr.hpp" ]]; then
	if [[ -x "$ROOT/../hyprframes/fetch-third-party.sh" ]]; then
		dest="$ROOT/third_party/hyprutils-0.13"
		mkdir -p "$ROOT/third_party"
		# Reuse the hyprframes header fetch, then copy the tree across.
		"$ROOT/../hyprframes/fetch-third-party.sh"
		if [[ -d "$ROOT/../hyprframes/third_party/hyprutils-0.13" ]]; then
			rm -rf "$dest"
			cp -a "$ROOT/../hyprframes/third_party/hyprutils-0.13" "$dest"
		fi
	fi
fi

echo "==> build hyprbars"
make -C "$ROOT" -j"$(nproc)"
[[ -f "$BUILT" ]] || { echo "build.sh: missing $BUILT" >&2; exit 1; }

echo "==> install $SO_NAME"
mkdir -p "$(dirname "$USER_DEST")"
cp -f "$BUILT" "$USER_DEST"
PLUGIN_LINE="plugin = ${USER_DEST}"
echo "installed $USER_DEST"
if mkdir -p "$(dirname "$SYS_DEST")" 2>/dev/null && cp -f "$BUILT" "$SYS_DEST" 2>/dev/null; then
	PLUGIN_LINE="plugin = ${SYS_DEST}"
	echo "installed $SYS_DEST"
elif command -v sudo >/dev/null 2>&1 && sudo mkdir -p "$(dirname "$SYS_DEST")" && sudo cp -f "$BUILT" "$SYS_DEST"; then
	PLUGIN_LINE="plugin = ${SYS_DEST}"
	echo "installed $SYS_DEST"
fi

echo "==> enable for the next Hyprland session"
if [[ ! -f "$CONF" ]]; then
	echo "no $CONF — plugin is installed; add: $PLUGIN_LINE"
	exit 0
fi
python3 - "$CONF" "$PLUGIN_LINE" <<'PY'
from pathlib import Path
import re
import sys

conf, line = Path(sys.argv[1]), sys.argv[2]
text = conf.read_text()
text2, n = re.subn(
    r"(?m)^[ \t]*plugin = .*/libhyprbars\.so[ \t]*$",
    line,
    text,
    count=1,
)
if n:
    conf.write_text(text2)
    print(f"refreshed plugin= in {conf}")
    raise SystemExit(0)
block = (
    "# hyprbars titlebar. Load after hyprframes.\n"
    "# Do not hyprctl plugin load / reload while hyprbars is already up.\n"
    f"{line}\n"
)
m = re.search(r"(?m)^[ \t]*plugin = .*/libhyprframes\.so[ \t]*$", text)
if m:
    insert = m.end()
    if insert < len(text) and text[insert] == "\n":
        insert += 1
    text = text[:insert] + block + text[insert:]
else:
    text = text.rstrip() + "\n\n" + block
conf.write_text(text)
print(f"updated {conf}")
PY
echo "armed $PLUGIN_LINE"
echo "Log out and start a new Hyprland session. Do not hyprctl plugin load / reload."
