# hyprbars (Neuronix)

Fork of [hyprwm/hyprland-plugins hyprbars](https://github.com/hyprwm/hyprland-plugins/tree/main/hyprbars) for Hyprland **0.55.x**, with Neuronix extras:

- Two-stop **gradient** fill (`bar_color` / `bar_color2`, inactive pair, `bar_gradient`)
- Live **`hyprbarsgradient`** / **`hyprbarsfill`** dispatchers (gtk-theme sync)
- **`hyprbars-button` replace-in-place** by action (no duplicate buttons from theme keywords)
- **`bar_image`**: repeating PNG titlebar background with transparency

## Build

Needs `hyprland-dev` matching the running compositor and `pangocairo`.

```bash
cd Packages/hyprbars
make -j"$(nproc)"
mkdir -p ~/.local/lib/hyprland/plugins
cp -f hyprbars.so ~/.local/lib/hyprland/plugins/libhyprbars.so
```

Load on next Hyprland login via `neuronix-ensure-hyprbars` (prefers `~/.local` then `/usr/local`). Do **not** `hyprctl plugin load` after hyprbars is already up, and do **not** `hyprctl reload` on this machine.

## Config (`plugin { hyprbars { … } }`)

| option | meaning |
| --- | --- |
| `bar_image` | Absolute PNG path. Empty = off. |
| `bar_image_opacity` | 0–1 multiplier on the PNG (and its alpha). |
| `bar_image_scale` | Tile size vs native pixels × monitor scale. |
| `bar_color` / `bar_color2` | Gradient stops (0 for color2 = solid). |
| `bar_color_inactive` / `bar_color_inactive2` | Unfocused stops. |
| `bar_gradient` | `ltr` or `rtl`. |

The image is drawn **on top of** the solid/gradient fill and **under** the title and buttons, so PNG alpha shows the fill through.

## ISO

`neuronix-iso/setup.sh` stages this tree to `/usr/src/neuronix/hyprbars`. Hook `998-neuronix-hyprspace` builds and installs `libhyprbars.so` into `/usr/local/lib/hyprland/plugins/` and the distro plugin dir. Example tile: `/usr/share/neuronix/hyprbars/tile-check.png`.
