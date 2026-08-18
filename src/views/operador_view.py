import pyqtgraph as pg
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
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
_FACE_ICON_SIZE = 16


def _build_face_icon(ok: bool) -> QIcon:
    pixmap = QPixmap(_FACE_ICON_SIZE, _FACE_ICON_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(_OK_COLOR if ok else _NG_COLOR)))
    painter.drawEllipse(1, 1, _FACE_ICON_SIZE - 2, _FACE_ICON_SIZE - 2)

    painter.setBrush(QBrush(QColor("white")))
    painter.drawEllipse(QRectF(4.5, 5.5, 2, 2))
    painter.drawEllipse(QRectF(9.5, 5.5, 2, 2))

    mouth = QPainterPath()
    if ok:
        mouth.moveTo(4, 10)
        mouth.quadTo(8, 13, 12, 10)
    else:
        mouth.moveTo(4, 12)
        mouth.quadTo(8, 9, 12, 12)

    pen = QPen(QColor("white"))
    pen.setWidthF(1.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(mouth)

    painter.end()
    return QIcon(pixmap)


class OperadorView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._pelicula_items: dict[tuple[str, str], QTreeWidgetItem] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._roi_items: list[pg.ROI] = []
        self._roi_labels: dict[str, pg.TextItem] = {}

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

        self.send_button = QPushButton("Enviar")

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.send_button)

        bottom_right_area = QWidget()
        bottom_right_area.setMinimumHeight(160)
        bottom_right_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        bottom_right_layout = QVBoxLayout(bottom_right_area)
        bottom_right_layout.addLayout(er_layout)
        bottom_right_layout.addStretch()
        bottom_right_layout.addLayout(button_layout)

        right_layout = QVBoxLayout()
        right_layout.addWidget(self.image_view, stretch=2)
        right_layout.addWidget(bottom_right_area, stretch=1)

        main_layout = QHBoxLayout(self)
        main_layout.addLayout(left_layout, stretch=1)
        main_layout.addLayout(right_layout, stretch=2)

    def show_image(self, image) -> None:
        self.image_item.setImage(image)

    def set_rois(self, rois: list[dict]) -> None:
        for item in self._roi_items:
            self.image_view.removeItem(item)
        for label_item in self._roi_labels.values():
            self.image_view.removeItem(label_item)
        self._roi_items = []
        self._roi_labels = {}

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

            label_item = pg.TextItem(
                roi["name"], color="w", anchor=(0, 1), fill=pg.mkBrush(0, 0, 0, 180)
            )
            label_item.setPos(roi_item.mapToParent(pg.Point(0, 0)))
            self.image_view.addItem(label_item)
            self._roi_labels[roi["name"]] = label_item

    def update_roi_scores(self, results: list[dict]) -> None:
        for result in results:
            old_label = self._roi_labels.get(result["name"])
            if old_label is None:
                continue
            pos = old_label.pos()
            self.image_view.removeItem(old_label)

            color = _OK_COLOR if result["ok"] else _NG_COLOR
            new_label = pg.TextItem(
                f"{result['name']}: {result['score']:.1f}%",
                color="w",
                anchor=(0, 1),
                fill=pg.mkBrush(color),
            )
            new_label.setPos(pos)
            self.image_view.addItem(new_label)
            self._roi_labels[result["name"]] = new_label

    def populate_tree(self, cameras: dict[str, list[str]]) -> None:
        self.tree.clear()
        self._pelicula_items = {}
        for camera_name, peliculas in cameras.items():
            camera_item = QTreeWidgetItem([camera_name])
            for pelicula_name in peliculas:
                child_item = QTreeWidgetItem([pelicula_name])
                camera_item.addChild(child_item)
                self._pelicula_items[(camera_name, pelicula_name)] = child_item
            self.tree.addTopLevelItem(camera_item)
        self.tree.expandAll()

    def clear_test_results(self) -> None:
        for (_, pelicula_name), item in self._pelicula_items.items():
            item.setText(0, pelicula_name)
            item.setIcon(0, QIcon())

    def set_test_results(self, camera: str, results: list[dict]) -> None:
        for result in results:
            item = self._pelicula_items.get((camera, result["name"]))
            if item is None:
                continue
            item.setText(0, result["name"])
            item.setIcon(0, _build_face_icon(result["ok"]))

    def show_result(self, ok: bool) -> None:
        color = _OK_COLOR if ok else _NG_COLOR
        self._paint_result(color, "OK" if ok else "NG", _RESULT_TEXT_COLOR)

    def clear_result(self) -> None:
        self._paint_result(_NEUTRAL_COLOR, "", _NEUTRAL_TEXT_COLOR)

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
