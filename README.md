# hyprbars

Fork of [hyprwm/hyprland-plugins hyprbars](https://github.com/hyprwm/hyprland-plugins/tree/main/hyprbars) for Hyprland **0.55.x**, with hyprCore Linux extras:

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

Load the plugin from `~/.local/lib/hyprland/plugins` or `/usr/local/lib/hyprland/plugins` on the next Hyprland login. Do **not** `hyprctl plugin load` after hyprbars is already up, and do **not** `hyprctl reload` on this machine.

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

Example tiles are in `examples/`. Copy `hyprbars.so` to `libhyprbars.so` in the Hyprland plugin directory.

## License

GNU General Public License v3.0. See [LICENSE](LICENSE).

This tree is a fork of [hyprwm/hyprland-plugins hyprbars](https://github.com/hyprwm/hyprland-plugins/tree/main/hyprbars). The original plugin is BSD 3-Clause, Copyright (c) 2023, Hypr Development. That notice is kept in [NOTICE](NOTICE).
