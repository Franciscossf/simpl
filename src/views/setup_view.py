import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_DEFAULT_ROI_POS = (10, 10)
_DEFAULT_ROI_SIZE = (80, 80)


class SetupView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._roi_items: dict[str, pg.ROI] = {}
        self._current_frame = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.camera_selector = QComboBox()
        self.toggle_camera_button = QPushButton("Ligar")

        camera_row = QHBoxLayout()
        camera_row.addWidget(self.camera_selector)
        camera_row.addWidget(self.toggle_camera_button)

        self.image_view = pg.PlotWidget()
        self.image_view.setAspectLocked(True)
        self.image_view.hideAxis("bottom")
        self.image_view.hideAxis("left")
        self.image_view.getViewBox().invertY(True)
        self.image_item = pg.ImageItem()
        self.image_view.addItem(self.image_item)

        self.roi_list = QListWidget()

        self.add_roi_button = QPushButton("Adicionar ROI")
        self.remove_roi_button = QPushButton("Remover ROI")
        self.import_button = QPushButton("Importar modelo")
        self.save_button = QPushButton("Salvar")

        roi_buttons_layout = QHBoxLayout()
        roi_buttons_layout.addWidget(self.add_roi_button)
        roi_buttons_layout.addWidget(self.remove_roi_button)

        side_layout = QVBoxLayout()
        side_layout.addLayout(camera_row)
        side_layout.addWidget(self.roi_list)
        side_layout.addLayout(roi_buttons_layout)
        side_layout.addWidget(self.import_button)
        side_layout.addStretch()
        side_layout.addWidget(self.save_button)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(self.image_view, stretch=3)
        main_layout.addLayout(side_layout, stretch=1)

    def set_cameras(self, cameras: list[str]) -> None:
        self.camera_selector.clear()
        self.camera_selector.addItems(cameras)

    def show_frame(self, image) -> None:
        self._current_frame = image
        self.image_item.setImage(image)

    def get_current_frame(self):
        return self._current_frame

    def clear_frame(self) -> None:
        self._current_frame = None
        self.image_item.clear()

    def set_camera_connected(self, connected: bool) -> None:
        self.toggle_camera_button.setText("Desligar" if connected else "Ligar")
        self.camera_selector.setEnabled(not connected)

    def show_camera_error(self, message: str) -> None:
        QMessageBox.warning(self, "Camera", message)

    def prompt_roi_name(self) -> str | None:
        name, confirmed = QInputDialog.getText(self, "Nova ROI", "Nome da pelicula:")
        if confirmed and name.strip():
            return name.strip()
        return None

    def clear_rois(self) -> None:
        for roi_item in self._roi_items.values():
            self.image_view.removeItem(roi_item)
        self._roi_items = {}
        self.roi_list.clear()

    def add_roi_item(
        self,
        name: str,
        x: float = _DEFAULT_ROI_POS[0],
        y: float = _DEFAULT_ROI_POS[1],
        w: float = _DEFAULT_ROI_SIZE[0],
        h: float = _DEFAULT_ROI_SIZE[1],
        angle: float = 0.0,
    ) -> None:
        roi_item = pg.ROI(pos=(x, y), size=(w, h), angle=angle, movable=True)
        roi_item.addScaleHandle((1, 1), (0, 0))
        roi_item.addRotateHandle((0, 0), (0.5, 0.5))
        roi_item.setPen(pg.mkPen("y", width=2))
        self.image_view.addItem(roi_item)
        self._roi_items[name] = roi_item
        self.roi_list.addItem(QListWidgetItem(name))

    def remove_roi_item(self, name: str) -> None:
        roi_item = self._roi_items.pop(name, None)
        if roi_item is not None:
            self.image_view.removeItem(roi_item)
        for item in self.roi_list.findItems(name, Qt.MatchFlag.MatchExactly):
            self.roi_list.takeItem(self.roi_list.row(item))

    def selected_roi_name(self) -> str | None:
        item = self.roi_list.currentItem()
        return item.text() if item is not None else None

    def get_rois_geometry(self) -> list[dict]:
        rois = []
        for name, roi_item in self._roi_items.items():
            pos = roi_item.pos()
            size = roi_item.size()
            rois.append(
                {
                    "name": name,
                    "x": pos.x(),
                    "y": pos.y(),
                    "w": size.x(),
                    "h": size.y(),
                    "angle": roi_item.angle(),
                }
            )
        return rois

    def prompt_model_name(self, default: str = "") -> str | None:
        name, confirmed = QInputDialog.getText(
            self, "Salvar modelo", "Nome do modelo da placa:", text=default
        )
        if confirmed and name.strip():
            return name.strip()
        return None

    def prompt_model_to_import(self, models: list[str]) -> str | None:
        if not models:
            QMessageBox.information(
                self, "Importar modelo", "Nenhum modelo salvo encontrado."
            )
            return None
        name, confirmed = QInputDialog.getItem(
            self, "Importar modelo", "Selecione o modelo:", models, editable=False
        )
        if confirmed and name:
            return name
        return None

    def show_imported_message(self, model_name: str) -> None:
        QMessageBox.information(
            self, "Importar modelo", f"Modelo '{model_name}' importado com sucesso."
        )

    def confirm_save(self, model_name: str) -> bool:
        answer = QMessageBox.question(
            self,
            "Salvar",
            f"Deseja salvar as ROIs de todas as cameras no modelo '{model_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def show_saved_message(self, model_name: str) -> None:
        QMessageBox.information(
            self, "Salvar", f"Modelo '{model_name}' salvo com sucesso."
        )
