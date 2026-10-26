# Else exist specifically for clang
ifeq ($(CXX),g++)
    EXTRA_FLAGS = --no-gnu-unique
else
    EXTRA_FLAGS =
endif

CXXFLAGS ?= -O2
CXXFLAGS += -shared -fPIC -std=c++2b -Wno-c++11-narrowing
# libhyprutils 0.14 made operator bool explicit; Hyprland 0.55.2 headers need 0.13.
INCLUDES = -Ithird_party/hyprutils-0.13 `pkg-config --cflags pixman-1 libdrm hyprland libinput libudev wayland-server xkbcommon pangocairo`
LIBS = `pkg-config --libs pangocairo`

SRC = main.cpp barDeco.cpp BarPassElement.cpp BarTextures.cpp
TARGET = hyprbars.so

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $(EXTRA_FLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

clean:
	rm ./$(TARGET)

meson-build:
	mkdir -p build
	cd build && meson .. && ninja

.PHONY: all meson-build clean
