import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

print("=" * 60)
print("BLOCK 2.1 — detect_figures() test")
print("=" * 60)

import os
import cv2
import numpy as np

from parser.figure_detector import detect_figures, is_complex_figure

# Create test images
def make_test_image(path, kind="map"):
    h, w = 600, 800
    img = np.ones((h, w, 3), dtype=np.uint8) * 240  # light gray background

    if kind == "table":
        # Draw horizontal lines → should be detected as table
        for y in range(100, 500, 50):
            cv2.line(img, (50, y), (750, y), (0, 0, 0), 2)
        for x in range(50, 750, 100):
            cv2.line(img, (x, 100), (x, 450), (0, 0, 0), 1)

    elif kind == "map":
        # Draw a big colored region → should be detected as figure
        cv2.rectangle(img, (100, 100), (700, 500), (100, 180, 100), -1)
        cv2.ellipse(img, (400, 300), (150, 100), 0, 0, 360, (50, 100, 200), -1)
        # Add some contour lines
        for r in range(50, 300, 40):
            cv2.circle(img, (400, 300), r, (0, 80, 0), 1)

    elif kind == "text":
        # Plain text-like page — no large blobs
        pass  # leave as blank gray

    elif kind == "empty":
        img = np.ones((h, w, 3), dtype=np.uint8) * 255  # pure white

    cv2.imwrite(path, img)
    return path

os.makedirs("tests/tmp_images", exist_ok=True)

table_img  = make_test_image("tests/tmp_images/table.png",  "table")
map_img    = make_test_image("tests/tmp_images/map.png",    "map")
text_img   = make_test_image("tests/tmp_images/text.png",   "text")
empty_img  = make_test_image("tests/tmp_images/empty.png",  "empty")

def run_check(label, condition):
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {label}")
    return condition

results = []

# Test table detection
table_result = detect_figures(table_img)
print(f"\nTable image → {table_result}")
results.append(run_check("Table detected (type='table' or non-empty)",
    len(table_result) > 0))

# Test map detection
map_result = detect_figures(map_img)
print(f"\nMap image → {map_result}")
results.append(run_check("Map/figure detected",
    len(map_result) > 0 and any(r["type"] == "figure" for r in map_result)))

# Test empty page — no false positives
empty_result = detect_figures(empty_img)
print(f"\nEmpty image → {empty_result}")
results.append(run_check("Empty page → no figures (no false positives)",
    len(empty_result) == 0))

# Test return structure
if map_result:
    block = map_result[0]
    has_bbox = "bbox" in block and len(block["bbox"]) == 4
    has_type = block["type"] in ("figure", "table")
    has_conf = "confidence" in block and 0 < block["confidence"] <= 1.0
    results.append(run_check("Return structure: bbox[4], type, confidence",
        has_bbox and has_type and has_conf))

# is_complex_figure test
results.append(run_check("is_complex_figure(table) == True",
    is_complex_figure(table_img) == True))
results.append(run_check("is_complex_figure(empty) == False",
    is_complex_figure(empty_img) == False))

print()
passed = sum(results)
total = len(results)
print(f"RESULT: {passed}/{total}")
if passed == total:
    print("STATUS: ✅ BLOCK 2.1 WORKS")
else:
    print("STATUS: ⚠️ PARTIAL")
