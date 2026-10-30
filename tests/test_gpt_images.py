import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/gpt_images.py"
spec = importlib.util.spec_from_file_location("gpt_images", SCRIPT)
gpt_images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gpt_images)


def test_cut_falls_back_to_strokes_when_lines_overlap_in_height(tmp_path):
    img = np.zeros((60, 90, 4), np.uint8)
    img[0:10, 0:50] = 255
    img[20:40, 0:30] = 255
    img[35:55, 40:80] = 255
    path = tmp_path / "결과.png"
    Image.fromarray(img, "RGBA").save(path)
    assert [p.shape[:2] for p in gpt_images._cut(path, 3)] == [(10, 50), (20, 30), (20, 40)]
