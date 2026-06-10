import cv2
import numpy as np
from typing import List, Dict, Any


def detect_figures(image_path: str) -> List[Dict[str, Any]]:
    """
    Detects figure/table regions on a page image.
    Returns a list of blocks: [{"bbox": [x0,y0,x1,y1], "type": "figure|table", "confidence": 0.9}]
    """
    img = cv2.imread(image_path)
    if img is None:
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Skip completely empty (white) pages — no false positives
    if cv2.countNonZero(cv2.bitwise_not(gray)) < 100:
        return []

    results = []

    # --- Table detection: look for horizontal line clusters ---
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100,
                             minLineLength=max(50, w // 8), maxLineGap=10)

    horizontal_lines = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 5:  # horizontal
                horizontal_lines.append((x1, y1, x2, y2))

    if len(horizontal_lines) >= 3:
        # Estimate table bbox from the line cluster
        xs = [pt for seg in horizontal_lines for pt in (seg[0], seg[2])]
        ys = [pt for seg in horizontal_lines for pt in (seg[1], seg[3])]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        results.append({
            "bbox": [x0, y0, x1, y1],
            "type": "table",
            "confidence": round(min(0.99, 0.6 + len(horizontal_lines) * 0.03), 2),
        })

    # --- Figure detection: large coloured / dense-pixel blobs ---
    # Use contour analysis on the original image to find large non-text regions
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    page_area = h * w

    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Only consider blobs that are at least 5% of the page
        if area < page_area * 0.05:
            continue

        rect = cv2.boundingRect(cnt)
        cx0, cy0, cw, ch = rect
        cx1, cy1 = cx0 + cw, cy0 + ch
        aspect = cw / max(ch, 1)

        # Skip very wide, thin strips (likely text paragraphs / horizontal rules)
        if aspect > 8 or ch < 30:
            continue

        # Check overlap with already-found table bbox to avoid duplicate
        already_covered = False
        for existing in results:
            ex0, ey0, ex1, ey1 = existing["bbox"]
            inter_x = max(0, min(cx1, ex1) - max(cx0, ex0))
            inter_y = max(0, min(cy1, ey1) - max(cy0, ey0))
            if inter_x * inter_y > 0.5 * area:
                already_covered = True
                break

        if already_covered:
            continue

        confidence = round(min(0.97, 0.65 + area / page_area), 2)
        results.append({
            "bbox": [cx0, cy0, cx1, cy1],
            "type": "figure",
            "confidence": confidence,
        })

    return results


def is_complex_figure(image_path: str) -> bool:
    """
    Returns True if the image is complex (geological map / table with lines)
    and should be routed to Colab Qwen instead of local Moondream.
    """
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return False

    edges = cv2.Canny(img, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)

    horizontal_lines = 0
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(y1 - y2) < 5:
                horizontal_lines += 1

    if horizontal_lines >= 3:
        return True  # Table → complex

    non_zero = cv2.countNonZero(edges)
    total_pixels = img.shape[0] * img.shape[1]

    # Many edge pixels = complex image (map, graph)
    if non_zero / total_pixels > 0.03:
        return True

    return False
