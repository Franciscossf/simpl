import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

_NEUTRAL_COLOR = "#f0f0f0"
_NEUTRAL_TEXT_COLOR = "#000000"
_OK_COLOR = "#2e7d32"
_NG_COLOR = "#c62828"
_RESULT_TEXT_COLOR = "#ffffff"


class OperadorView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._roi_items: list[pg.ROI] = []

        self.model_label = QLabel("Nenhum modelo carregado")
        self.import_model_button = QPushButton("Importar modelo")

        model_row = QHBoxLayout()
        model_row.addWidget(self.model_label, stretch=1)
        model_row.addWidget(self.import_model_button)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Tree")
        self.tree.setMinimumWidth(260)

        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.result_frame = QFrame()
        self.result_frame.setFrameShape(QFrame.Shape.Box)
        self.result_frame.setMinimumHeight(160)
        self.result_frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        result_layout = QVBoxLayout(self.result_frame)
        result_layout.addWidget(self.result_label)

        self.clear_result()

        left_layout = QVBoxLayout()
        left_layout.addLayout(model_row)
        left_layout.addWidget(self.tree, stretch=2)
        left_layout.addWidget(self.result_frame, stretch=1)

        self.image_view = pg.PlotWidget()
        self.image_view.setAspectLocked(True)
        self.image_view.hideAxis("bottom")
        self.image_view.hideAxis("left")
        self.image_view.getViewBox().invertY(True)
        self.image_item = pg.ImageItem()
        self.image_view.addItem(self.image_item)

        self.er_field = QLineEdit()
        er_layout = QHBoxLayout()
        er_layout.addWidget(QLabel("ER"))
        er_layout.addWidget(self.er_field)
        er_layout.addStretch()

        er_area = QWidget()
        er_area.setMinimumHeight(70)
        er_area.setLayout(er_layout)

        self.send_button = QPushButton("Enviar")

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.send_button)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.image_view)
        right_layout.addWidget(er_area)
        right_layout.addLayout(button_layout)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=2)

    def show_image(self, image) -> None:
        self.image_item.setImage(image)

    def set_rois(self, rois: list[dict]) -> None:
        for item in self._roi_items:
            self.image_view.removeItem(item)
        self._roi_items = []

        for roi in rois:
            roi_item = pg.ROI(
                pos=(roi["x"], roi["y"]),
                size=(roi["w"], roi["h"]),
                angle=roi.get("angle", 0.0),
                movable=False,
            )
            roi_item.setPen(pg.mkPen("y", width=2))
            self.image_view.addItem(roi_item)
            self._roi_items.append(roi_item)

    def populate_tree(self, cameras: dict[str, list[str]]) -> None:
        self.tree.clear()
        for camera_name, peliculas in cameras.items():
            camera_item = QTreeWidgetItem([camera_name])
            for pelicula_name in peliculas:
                camera_item.addChild(QTreeWidgetItem([pelicula_name]))
            self.tree.addTopLevelItem(camera_item)
        self.tree.expandAll()

    def show_result(self, ok: bool) -> None:
        color = _OK_COLOR if ok else _NG_COLOR
        self._paint_result(color, "OK" if ok else "NG", _RESULT_TEXT_COLOR)

    def clear_result(self) -> None:
        self._paint_result(_NEUTRAL_COLOR, "OK ou NG", _NEUTRAL_TEXT_COLOR)

    def _paint_result(self, background_color: str, text: str, text_color: str) -> None:
        self.result_frame.setStyleSheet(f"background-color: {background_color};")
        self.result_label.setText(text)
        self.result_label.setStyleSheet(f"font-size: 32px; color: {text_color};")

    def clear_er_field(self) -> None:
        self.er_field.clear()

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Inspecao", message)

    def set_send_enabled(self, enabled: bool) -> None:
        self.send_button.setEnabled(enabled)

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

    def set_current_model(self, model_name: str) -> None:
        self.model_label.setText(f"Modelo: {model_name}")
