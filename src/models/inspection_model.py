import base64
import json

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal

from src.utils.paths import data_path


class InspectionModel(QObject):
    rois_changed = Signal()

    def __init__(self, camera_count: int = 4) -> None:
        super().__init__()
        self._cameras = [f"Camera {i:02d}" for i in range(1, camera_count + 1)]
        self._rois: dict[str, list[dict]] = {camera: [] for camera in self._cameras}
        self._reference_images: dict[str, list[np.ndarray]] = {}

    def get_cameras(self) -> list[str]:
        return self._cameras

    def get_tree_data(self) -> dict[str, list[str]]:
        return {
            camera: [roi["name"] for roi in rois]
            for camera, rois in self._rois.items()
        }

    def get_rois(self, camera: str) -> list[dict]:
        return self._rois.get(camera, [])

    def set_rois(self, camera: str, rois: list[dict]) -> None:
        self._rois[camera] = rois
        self.rois_changed.emit()

    def set_reference_images(self, camera: str, images: list[np.ndarray]) -> None:
        self._reference_images[camera] = images

    def get_reference_images(self, camera: str) -> list[np.ndarray]:
        return self._reference_images.get(camera, [])

    def get_reference_image(self, camera: str) -> np.ndarray | None:
        images = self._reference_images.get(camera)
        return images[-1] if images else None

    def save_model(self, model_name: str) -> None:
        target_dir = data_path("models", model_name)
        target_dir.mkdir(parents=True, exist_ok=True)

        data = {
            camera: {
                "rois": self._rois.get(camera, []),
                "images": [
                    self._encode_image(image)
                    for image in self._reference_images.get(camera, [])
                ],
            }
            for camera in self._cameras
        }

        (target_dir / "rois.json").write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        for old_image in target_dir.glob("Camera *.png"):
            old_image.unlink()

        for camera, images in self._reference_images.items():
            for index, image in enumerate(images, start=1):
                image_path = target_dir / f"{camera}_{index}.png"
                cv2.imwrite(str(image_path), image)

    def list_saved_models(self) -> list[str]:
        models_dir = data_path("models")
        if not models_dir.exists():
            return []
        return sorted(p.name for p in models_dir.iterdir() if p.is_dir())

    def load_model(self, model_name: str) -> bool:
        target_dir = data_path("models", model_name)
        target_file = target_dir / "rois.json"
        if not target_file.exists():
            return False

        saved_data = json.loads(target_file.read_text(encoding="utf-8"))
        for camera in self._cameras:
            camera_data = saved_data.get(camera, {})

            if isinstance(camera_data, list):
                # Formato antigo: lista de rois sem imagem embutida.
                self._rois[camera] = camera_data
                camera_data = {}
            else:
                self._rois[camera] = camera_data.get("rois", [])

            images = self._load_camera_images(target_dir, camera, camera_data)
            self._reference_images[camera] = images

        self.rois_changed.emit()
        return True

    def _load_camera_images(
        self, target_dir, camera: str, camera_data: dict
    ) -> list[np.ndarray]:
        encoded_images = camera_data.get("images")
        if encoded_images is not None:
            images = [self._decode_image(item) for item in encoded_images]
            images = [image for image in images if image is not None]
            if images:
                return images

        # Formato antigo: uma unica imagem embutida ou um unico arquivo .png.
        legacy_image = self._decode_image(camera_data.get("image"))
        if legacy_image is None:
            legacy_path = target_dir / f"{camera}.png"
            if legacy_path.exists():
                legacy_image = cv2.imread(str(legacy_path), cv2.IMREAD_GRAYSCALE)
        if legacy_image is not None:
            return [legacy_image]

        images = []
        index = 1
        while (target_dir / f"{camera}_{index}.png").exists():
            image = cv2.imread(str(target_dir / f"{camera}_{index}.png"), cv2.IMREAD_GRAYSCALE)
            if image is not None:
                images.append(image)
            index += 1
        return images

    @staticmethod
    def _encode_image(image: np.ndarray | None) -> str | None:
        if image is None:
            return None
        success, buffer = cv2.imencode(".png", image)
        if not success:
            return None
        return base64.b64encode(buffer).decode("ascii")

    @staticmethod
    def _decode_image(encoded: str | None) -> np.ndarray | None:
        if not encoded:
            return None
        buffer = base64.b64decode(encoded)
        return cv2.imdecode(np.frombuffer(buffer, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
