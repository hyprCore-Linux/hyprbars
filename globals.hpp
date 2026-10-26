#pragma once

#include <hyprland/src/plugins/PluginAPI.hpp>
#include <hyprland/src/render/Texture.hpp>
#include <hyprland/src/config/values/types/BoolValue.hpp>
#include <hyprland/src/config/values/types/IntValue.hpp>
#include <hyprland/src/config/values/types/FloatValue.hpp>
#include <hyprland/src/config/values/types/StringValue.hpp>
#include <hyprland/src/config/values/types/ColorValue.hpp>

#include <cstdint>
#include <string>
#include <vector>

inline HANDLE PHANDLE = nullptr;

struct SHyprButton {
    std::string          cmd     = "";
    bool                 userfg  = false;
    CHyprColor           fgcol   = CHyprColor(0, 0, 0, 0);
    CHyprColor           bgcol   = CHyprColor(0, 0, 0, 0);
    float                size    = 10;
    std::string          icon    = "";
    SP<Render::ITexture> iconTex;
};

class CHyprBar;

// Live override from hyprbarsgradient / hyprbarsfill (gtk-theme sync).
struct SBarGradientLive {
    CHyprColor  c1, c2, i1, i2;
    std::string dir = "ltr";
    bool        set = false;
};

struct SBarImageState {
    SP<Render::ITexture> tex;
    std::string          loadedPath;
    bool                 failed = false;
};

struct SGlobalState {
    std::vector<SHyprButton>  buttons;
    std::vector<WP<CHyprBar>> bars;
    uint32_t                  nobarRuleIdx      = 0;
    uint32_t                  barColorRuleIdx   = 0;
    uint32_t                  titleColorRuleIdx = 0;

    SBarGradientLive gradientLive;
    SBarImageState   barImage;

    // Cached 256×1 gradient strip (rebuilt when colors/dir change).
    SP<Render::ITexture> gradientTex;
    uint64_t             gradientKey = 0;

    struct {
        SP<Config::Values::CColorValue>  barColor, barColor2, barColorInactive, barColorInactive2, textColor, inactiveButtonColor;
        SP<Config::Values::CIntValue>    barHeight;
        SP<Config::Values::CIntValue>    barTextSize;
        SP<Config::Values::CIntValue>    barPadding;
        SP<Config::Values::CIntValue>    barButtonPadding;
        SP<Config::Values::CFloatValue>  barImageOpacity, barImageScale;
        SP<Config::Values::CBoolValue>   barBlur, barTitleEnabled, barPartOfWindow, barPrecedenceOverBorder, enabled, iconOnHover;
        SP<Config::Values::CStringValue> barTextFont, barTextAlign, barButtonsAlignment, onDoubleClick, barGradient, barImage;
    } config;
};

inline UP<SGlobalState> g_pGlobalState;

// Ensure bar_image PNG is loaded (lazy). Safe no-op if path empty/missing.
void hyprbarsEnsureBarImage();
// Build or reuse a horizontal gradient texture for the given colors.
SP<Render::ITexture> hyprbarsGradientTexture(const CHyprColor& a, const CHyprColor& b, bool rtl);
void                 hyprbarsInvalidateBarImage();
void                 hyprbarsInvalidateGradient();
