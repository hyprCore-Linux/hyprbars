#include "globals.hpp"

#include <cairo/cairo.h>
#include <filesystem>
#include <hyprland/src/debug/log/Logger.hpp>
#include <hyprland/src/render/Renderer.hpp>
#include <hyprland/src/render/OpenGL.hpp>

#include <cmath>
#include <cstring>

using namespace Render;

static uint64_t colorKey(const CHyprColor& c) {
    return (uint64_t)(std::lround(c.r * 255.0) & 0xFF) << 24 | (uint64_t)(std::lround(c.g * 255.0) & 0xFF) << 16 |
           (uint64_t)(std::lround(c.b * 255.0) & 0xFF) << 8 | (uint64_t)(std::lround(c.a * 255.0) & 0xFF);
}

void hyprbarsInvalidateBarImage() {
    if (!g_pGlobalState)
        return;
    g_pGlobalState->barImage.tex       = nullptr;
    g_pGlobalState->barImage.loadedPath.clear();
    g_pGlobalState->barImage.failed    = false;
}

void hyprbarsInvalidateGradient() {
    if (!g_pGlobalState)
        return;
    g_pGlobalState->gradientTex = nullptr;
    g_pGlobalState->gradientKey = 0;
}

void hyprbarsEnsureBarImage() {
    if (!g_pGlobalState || !g_pHyprRenderer)
        return;

    const auto path = g_pGlobalState->config.barImage ? g_pGlobalState->config.barImage->value() : "";
    if (path.empty()) {
        hyprbarsInvalidateBarImage();
        return;
    }

    if (g_pGlobalState->barImage.failed && g_pGlobalState->barImage.loadedPath == path)
        return;
    if (g_pGlobalState->barImage.tex && g_pGlobalState->barImage.loadedPath == path)
        return;

    hyprbarsInvalidateBarImage();
    g_pGlobalState->barImage.loadedPath = path;

    if (!std::filesystem::exists(path)) {
        Log::logger->log(Log::ERR, "[hyprbars] bar_image not found: {}", path);
        g_pGlobalState->barImage.failed = true;
        return;
    }

    cairo_surface_t* surf = cairo_image_surface_create_from_png(path.c_str());
    if (!surf || cairo_surface_status(surf) != CAIRO_STATUS_SUCCESS) {
        if (surf)
            cairo_surface_destroy(surf);
        Log::logger->log(Log::ERR, "[hyprbars] bar_image failed to load (need PNG): {}", path);
        g_pGlobalState->barImage.failed = true;
        return;
    }

    g_pGlobalState->barImage.tex    = g_pHyprRenderer->createTexture(surf);
    g_pGlobalState->barImage.failed = !g_pGlobalState->barImage.tex || g_pGlobalState->barImage.tex->m_texID == 0;
    cairo_surface_destroy(surf);

    if (g_pGlobalState->barImage.failed)
        Log::logger->log(Log::ERR, "[hyprbars] bar_image texture create failed: {}", path);
}

SP<ITexture> hyprbarsGradientTexture(const CHyprColor& a, const CHyprColor& b, bool rtl) {
    if (!g_pGlobalState || !g_pHyprRenderer)
        return nullptr;

    const uint64_t key = colorKey(a) ^ (colorKey(b) << 1) ^ (rtl ? 1ULL << 63 : 0);
    if (g_pGlobalState->gradientTex && g_pGlobalState->gradientKey == key)
        return g_pGlobalState->gradientTex;

    constexpr int W = 256;
    constexpr int H = 1;
    cairo_surface_t* surf = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, W, H);
    cairo_t*         cr   = cairo_create(surf);

    const CHyprColor left  = rtl ? b : a;
    const CHyprColor right = rtl ? a : b;

    cairo_pattern_t* pat = cairo_pattern_create_linear(0, 0, W, 0);
    cairo_pattern_add_color_stop_rgba(pat, 0.0, left.r, left.g, left.b, left.a);
    cairo_pattern_add_color_stop_rgba(pat, 1.0, right.r, right.g, right.b, right.a);
    cairo_set_source(cr, pat);
    cairo_paint(cr);
    cairo_pattern_destroy(pat);
    cairo_surface_flush(surf);

    g_pGlobalState->gradientTex = g_pHyprRenderer->createTexture(surf);
    g_pGlobalState->gradientKey = key;

    cairo_destroy(cr);
    cairo_surface_destroy(surf);

    return g_pGlobalState->gradientTex;
}
