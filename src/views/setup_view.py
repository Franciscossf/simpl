import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

_DEFAULT_ROI_POS = (10, 10)
_DEFAULT_ROI_SIZE = (80, 80)
_DEFAULT_THRESHOLD = 80.0
_ROI_COLOR = "y"
_ROI_SELECTED_COLOR = "r"


class SetupView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._roi_items: dict[str, pg.ROI] = {}
        self._roi_labels: dict[str, pg.TextItem] = {}
        self._roi_thresholds: dict[str, float] = {}
        self._current_frame = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.camera_selector = QComboBox()
        self.toggle_camera_button = QPushButton("Ligar")

        camera_row = QHBoxLayout()
        camera_row.addWidget(self.camera_selector)
        camera_row.addWidget(self.toggle_camera_button)

        self.autofocus_checkbox = QCheckBox("Foco automatico")
        self.autofocus_checkbox.setChecked(True)
        self.autofocus_checkbox.setEnabled(False)

        self.focus_slider = QSlider(Qt.Orientation.Horizontal)
        self.focus_slider.setRange(0, 255)
        self.focus_slider.setEnabled(False)

        focus_row = QHBoxLayout()
        focus_row.addWidget(QLabel("Foco"))
        focus_row.addWidget(self.focus_slider)

        self.image_view = pg.PlotWidget()
        self.image_view.setAspectLocked(True)
        self.image_view.hideAxis("bottom")
        self.image_view.hideAxis("left")
        self.image_view.getViewBox().invertY(True)
        self.image_item = pg.ImageItem()
        self.image_view.addItem(self.image_item)

        self.roi_list = QListWidget()

        self.threshold_spinbox = QDoubleSpinBox()
        self.threshold_spinbox.setRange(0.0, 100.0)
        self.threshold_spinbox.setSuffix(" %")
        self.threshold_spinbox.setValue(_DEFAULT_THRESHOLD)
        self.threshold_spinbox.setEnabled(False)

        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("Similaridade minima"))
        threshold_row.addWidget(self.threshold_spinbox)

        self.add_roi_button = QPushButton("Adicionar ROI")
        self.remove_roi_button = QPushButton("Remover ROI")
        self.import_button = QPushButton("Importar modelo")
        self.save_button = QPushButton("Salvar")

        roi_buttons_layout = QHBoxLayout()
        roi_buttons_layout.addWidget(self.add_roi_button)
        roi_buttons_layout.addWidget(self.remove_roi_button)

        side_layout = QVBoxLayout()
        side_layout.addLayout(camera_row)
        side_layout.addWidget(self.autofocus_checkbox)
        side_layout.addLayout(focus_row)
        side_layout.addWidget(self.roi_list)
        side_layout.addLayout(threshold_row)
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
        self.autofocus_checkbox.setEnabled(connected)
        self.focus_slider.setEnabled(connected and not self.autofocus_checkbox.isChecked())

    def set_focus_slider_enabled(self, enabled: bool) -> None:
        self.focus_slider.setEnabled(enabled)

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
        for label_item in self._roi_labels.values():
            self.image_view.removeItem(label_item)
        self._roi_items = {}
        self._roi_labels = {}
        self._roi_thresholds = {}
        self.roi_list.clear()

    def add_roi_item(
        self,
        name: str,
        x: float = _DEFAULT_ROI_POS[0],
        y: float = _DEFAULT_ROI_POS[1],
        w: float = _DEFAULT_ROI_SIZE[0],
        h: float = _DEFAULT_ROI_SIZE[1],
        angle: float = 0.0,
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        roi_item = pg.ROI(pos=(x, y), size=(w, h), angle=angle, movable=True)
        roi_item.addScaleHandle((1, 1), (0, 0))
        roi_item.addRotateHandle((0, 0), (0.5, 0.5))
        roi_item.setPen(pg.mkPen(_ROI_COLOR, width=2))
        self.image_view.addItem(roi_item)

        label_item = pg.TextItem(name, color=_ROI_COLOR, anchor=(0, 1))
        self.image_view.addItem(label_item)

        roi_item.sigRegionChanged.connect(
            lambda *_: self._update_roi_label_position(name)
        )

        self._roi_items[name] = roi_item
        self._roi_labels[name] = label_item
        self._roi_thresholds[name] = threshold
        self._update_roi_label_position(name)
        self.roi_list.addItem(QListWidgetItem(name))

    def _update_roi_label_position(self, name: str) -> None:
        roi_item = self._roi_items.get(name)
        label_item = self._roi_labels.get(name)
        if roi_item is None or label_item is None:
            return
        # A view usa invertY(True), entao o canto visualmente "de cima" e o
        # local (0, 0), nao (0, h) - y menor fica mais alto na tela.
        top_left = roi_item.mapToParent(pg.Point(0, 0))
        label_item.setPos(top_left)

    def remove_roi_item(self, name: str) -> None:
        roi_item = self._roi_items.pop(name, None)
        if roi_item is not None:
            self.image_view.removeItem(roi_item)
        label_item = self._roi_labels.pop(name, None)
        if label_item is not None:
            self.image_view.removeItem(label_item)
        self._roi_thresholds.pop(name, None)
        for item in self.roi_list.findItems(name, Qt.MatchFlag.MatchExactly):
            self.roi_list.takeItem(self.roi_list.row(item))

    def highlight_roi(self, name: str | None) -> None:
        for roi_name, roi_item in self._roi_items.items():
            color = _ROI_SELECTED_COLOR if roi_name == name else _ROI_COLOR
            roi_item.setPen(pg.mkPen(color, width=2))

    def selected_roi_name(self) -> str | None:
        item = self.roi_list.currentItem()
        return item.text() if item is not None else None

    def get_roi_threshold(self, name: str) -> float:
        return self._roi_thresholds.get(name, _DEFAULT_THRESHOLD)

    def set_roi_threshold(self, name: str, threshold: float) -> None:
        if name in self._roi_thresholds:
            self._roi_thresholds[name] = threshold

    def show_roi_threshold(self, threshold: float | None) -> None:
        self.threshold_spinbox.setEnabled(threshold is not None)
        self.threshold_spinbox.blockSignals(True)
        self.threshold_spinbox.setValue(
            threshold if threshold is not None else _DEFAULT_THRESHOLD
        )
        self.threshold_spinbox.blockSignals(False)

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
                    "threshold": self._roi_thresholds.get(name, _DEFAULT_THRESHOLD),
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
