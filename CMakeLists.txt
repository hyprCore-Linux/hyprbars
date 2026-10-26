cmake_minimum_required(VERSION 3.27)

project(hyprbars
    DESCRIPTION "hyprbars plugin for Hyprland"
    VERSION 0.1
)

set(CMAKE_CXX_STANDARD 23)

# libhyprutils 0.14 made operator bool explicit; Hyprland 0.55.2 needs 0.13 headers.
include_directories(BEFORE "${CMAKE_SOURCE_DIR}/third_party/hyprutils-0.13")

file(GLOB SRC "*.cpp")

add_library(hyprbars SHARED ${SRC})

find_package(PkgConfig REQUIRED)
pkg_check_modules(deps REQUIRED IMPORTED_TARGET
    hyprland
    libdrm
    libinput
    libudev
    pixman-1
    wayland-server
    xkbcommon
    pangocairo
)
target_link_libraries(hyprbars PRIVATE rt PkgConfig::deps)

install(TARGETS hyprbars)
