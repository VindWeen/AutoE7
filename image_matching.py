"""Small contour matching with bounded positional tolerance."""
import cv2
import numpy as np


def tolerant_edges(search, template, scales):
    """Return contour F1 score, allowing one pixel of anti-aliasing drift.

    Both coverage and precision matter: checking coverage alone incorrectly
    accepts dense artwork or unrelated icons near the story controls.
    """
    search_edges = cv2.Canny(search, 60, 140).astype(np.float32)/255
    kernel = np.ones((3, 3), dtype=np.uint8)
    nearby_search = cv2.dilate(search_edges, kernel)
    best = 0.0
    for scale in scales:
        scaled = cv2.resize(template, None, fx=scale, fy=scale)
        edges = cv2.Canny(scaled, 60, 140).astype(np.float32)/255
        if edges.shape[0] > search.shape[0] or edges.shape[1] > search.shape[1]:
            continue
        count = float(edges.sum())
        if count < 12:
            continue
        recall = cv2.matchTemplate(nearby_search, edges, cv2.TM_CCORR)/count
        hits = cv2.matchTemplate(search_edges, cv2.dilate(edges, kernel), cv2.TM_CCORR)
        total = cv2.matchTemplate(search_edges, np.ones_like(edges), cv2.TM_CCORR)
        precision = hits/np.maximum(total, 1)
        score = 2*recall*precision/np.maximum(recall+precision, 1e-6)
        best = max(best, float(score.max()))
    return min(best, 1.0)
