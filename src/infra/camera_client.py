import cv2


class CameraClient:
    def __init__(self, index: int) -> None:
        self._index = index
        self._capture: cv2.VideoCapture | None = None

    def connect(self) -> bool:
        self._capture = cv2.VideoCapture(self._index)
        return self._capture.isOpened()

    def read(self):
        if self._capture is None:
            return None
        ok, frame = self._capture.read()
        if not ok:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def set_autofocus(self, enabled: bool) -> None:
        if self._capture is not None:
            self._capture.set(cv2.CAP_PROP_AUTOFOCUS, 1.0 if enabled else 0.0)

    def set_focus(self, value: int) -> None:
        if self._capture is not None:
            self._capture.set(cv2.CAP_PROP_FOCUS, value)
