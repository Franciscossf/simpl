import cv2
import numpy as np
from skimage.metrics import structural_similarity


def crop_roi(image: np.ndarray, roi: dict) -> np.ndarray:
    x, y, w, h = int(round(roi["x"])), int(round(roi["y"])), int(round(roi["w"])), int(round(roi["h"]))
    angle = roi.get("angle", 0.0)

    if abs(angle) > 1e-3:
        center = (x + w / 2, y + h / 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))

    y0, y1 = max(y, 0), max(y + h, 0)
    x0, x1 = max(x, 0), max(x + w, 0)
    return image[y0:y1, x0:x1]


def compare_regions(reference: np.ndarray, live: np.ndarray) -> float:
    if reference.size == 0 or live.size == 0:
        return 0.0

    reference_gray = cv2.cvtColor(reference, cv2.COLOR_RGB2GRAY)
    live_gray = cv2.cvtColor(live, cv2.COLOR_RGB2GRAY)

    if live_gray.shape != reference_gray.shape:
        live_gray = cv2.resize(live_gray, (reference_gray.shape[1], reference_gray.shape[0]))

    score = structural_similarity(reference_gray, live_gray)
    return max(0.0, score) * 100.0


def compare_camera(
    reference_image: np.ndarray, live_image: np.ndarray, rois: list[dict]
) -> list[dict]:
    results = []
    for roi in rois:
        reference_crop = crop_roi(reference_image, roi)
        live_crop = crop_roi(live_image, roi)
        score = compare_regions(reference_crop, live_crop)
        results.append({"name": roi["name"], "score": score})
    return results
