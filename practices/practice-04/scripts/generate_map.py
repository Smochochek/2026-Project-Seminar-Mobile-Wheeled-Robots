#!/usr/bin/env python3
import os
import numpy as np
from PIL import Image

# Параметры карты в точном соответствии со сценой Webots:
# Арена RectangleArena: floorSize 6 6, wallThickness 0.03 м -> наружный габарит 6.06 x 6.06 м
# Центр арены (0, 0)
resolution = 0.01  # 1 см на пиксель (0.01 м)
origin_x = -3.03
origin_y = -3.03
size_x = 6.06
size_y = 6.06

width = int(round(size_x / resolution))   # 606 пикселей
height = int(round(size_y / resolution)) # 606 пикселей

# 254 = свободное пространство (белый цвет)
# 0   = занято / препятствие (черный цвет)
grid = np.full((height, width), 254, dtype=np.uint8)

def mark_box(x_min, x_max, y_min, y_max, val=0):
    col_min = max(0, int(round((x_min - origin_x) / resolution)))
    col_max = min(width, int(round((x_max - origin_x) / resolution)))
    row_min = max(0, int(round((y_min - origin_y) / resolution)))
    row_max = min(height, int(round((y_max - origin_y) / resolution)))
    grid[row_min:row_max, col_min:col_max] = val

# 1. Внешние стены арены (толщина 0.03 м, полуразмер арены 3.0 м)
mark_box(-3.03, -3.00, -3.03, 3.03)  # Западная
mark_box(3.00, 3.03, -3.03, 3.03)   # Восточная
mark_box(-3.03, 3.03, -3.03, -3.00) # Южная
mark_box(-3.03, 3.03, 3.00, 3.03)   # Северная

# 2. Цифра «1» из practice-02:
# translation = -0.45 0, size = 0.12 0.9 0.2
mark_box(-0.45 - 0.06, -0.45 + 0.06, -0.45, 0.45)

# 3. Цифра «6» из practice-02:
# translation = 0.45 0
# TOP_BAR: dx=0, dy=0.40, size=0.44 0.10 -> x in [0.45-0.22, 0.45+0.22], y in [0.40-0.05, 0.40+0.05]
mark_box(0.45 - 0.22, 0.45 + 0.22, 0.40 - 0.05, 0.40 + 0.05)
# LEFT_BAR: dx=-0.17, dy=0, size=0.10 0.90 -> x in [0.45-0.17-0.05, 0.45-0.17+0.05], y in [-0.45, 0.45]
mark_box(0.45 - 0.17 - 0.05, 0.45 - 0.17 + 0.05, -0.45, 0.45)
# MID_BAR: dx=0, dy=0, size=0.44 0.10 -> x in [0.45-0.22, 0.45+0.22], y in [-0.05, 0.05]
mark_box(0.45 - 0.22, 0.45 + 0.22, -0.05, 0.05)
# BOT_BAR: dx=0, dy=-0.40, size=0.44 0.10 -> x in [0.45-0.22, 0.45+0.22], y in [-0.45, -0.35]
mark_box(0.45 - 0.22, 0.45 + 0.22, -0.40 - 0.05, -0.40 + 0.05)
# RIGHT_BOT_BAR: dx=0.17, dy=-0.20, size=0.10 0.40 -> x in [0.45+0.17-0.05, 0.45+0.17+0.05], y in [-0.40, 0.0]
mark_box(0.45 + 0.17 - 0.05, 0.45 + 0.17 + 0.05, -0.20 - 0.20, -0.20 + 0.20)

image_data = np.flipud(grid)

script_dir = os.path.dirname(os.path.abspath(__file__))
maps_dir = os.path.join(script_dir, "..", "maps")
os.makedirs(maps_dir, exist_ok=True)

png_path = os.path.join(maps_dir, "map.png")
img = Image.fromarray(image_data)
img.save(png_path)

pgm_path = os.path.join(maps_dir, "map.pgm")
with open(pgm_path, "w") as f:
    f.write(f"P2\n{width} {height}\n255\n")
    for row in image_data:
        f.write(" ".join(map(str, row)) + "\n")

yaml_path = os.path.join(maps_dir, "map.yaml")
with open(yaml_path, "w") as f:
    f.write(f"""image: map.png
mode: trinary
resolution: {resolution}
origin: [{origin_x}, {origin_y}, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.25
""")

print(f"Карта успешно сгенерирована под точные размеры practice-02:\n - {png_path}\n - {yaml_path}")
