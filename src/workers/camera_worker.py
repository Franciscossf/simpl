from PySide6.QtCore import QThread, Signal

from src.infra.camera_client import CameraClient


class CameraWorker(QThread):
    frame_ready = Signal(object)
    error = Signal(str)
    stopped = Signal()

    def __init__(self, camera_index: int, parent=None) -> None:
        super().__init__(parent)
        self._camera_index = camera_index
        self._pending_autofocus: bool | None = None
        self._pending_focus: int | None = None

    def request_autofocus(self, enabled: bool) -> None:
        self._pending_autofocus = enabled

    def request_focus(self, value: int) -> None:
        self._pending_focus = value

    def run(self) -> None:
        client = CameraClient(self._camera_index)
        if not client.connect():
            self.error.emit(f"Nao foi possivel abrir a camera {self._camera_index}.")
            return

        while not self.isInterruptionRequested():
            if self._pending_autofocus is not None:
                client.set_autofocus(self._pending_autofocus)
                self._pending_autofocus = None
            if self._pending_focus is not None:
                client.set_focus(self._pending_focus)
                self._pending_focus = None

            frame = client.read()
            if frame is not None:
                self.frame_ready.emit(frame)
            self.msleep(30)

        client.release()
        self.stopped.emit()
