from PySide6.QtCore import QThread, Signal

from src.infra.camera_client import CameraClient
from src.models import similarity


class InspectionWorker(QThread):
    camera_captured = Signal(str, object)
    finished_ok = Signal(dict)
    error = Signal(str)

    def __init__(self, cameras: dict[str, dict], threshold: float, parent=None) -> None:
        """cameras: {camera_name: {"index": int, "reference_image": ndarray, "rois": list[dict]}}"""
        super().__init__(parent)
        self._cameras = cameras
        self._threshold = threshold

    def run(self) -> None:
        try:
            report: dict[str, dict] = {}
            overall_ok = True

            for camera_name, data in self._cameras.items():
                client = CameraClient(data["index"])
                if not client.connect():
                    self.error.emit(f"Nao foi possivel abrir a {camera_name}.")
                    return

                live_image = client.read()
                client.release()

                if live_image is None:
                    self.error.emit(f"Nao foi possivel capturar imagem da {camera_name}.")
                    return

                self.camera_captured.emit(camera_name, live_image)

                roi_results = similarity.compare_camera(
                    data["reference_image"], live_image, data["rois"]
                )
                camera_ok = all(r["score"] >= self._threshold for r in roi_results)
                overall_ok = overall_ok and camera_ok
                report[camera_name] = {"rois": roi_results, "ok": camera_ok}

            self.finished_ok.emit({"ok": overall_ok, "cameras": report})
        except Exception as error:
            self.error.emit(str(error))
