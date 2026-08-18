from src.models.inspection_model import InspectionModel
from src.views.operador_view import OperadorView
from src.workers.inspection_worker import InspectionWorker


class OperadorController:
    def __init__(self, model: InspectionModel, view: OperadorView) -> None:
        self.model = model
        self.view = view
        self._inspection_worker: InspectionWorker | None = None
        self._current_cameras: dict = {}
        self._connect_signals()
        self._load_initial_data()

    def _connect_signals(self) -> None:
        self.view.send_button.clicked.connect(self._on_send_clicked)
        self.view.import_model_button.clicked.connect(self._on_import_model)
        self.view.tree.currentItemChanged.connect(self._on_tree_selection_changed)
        self.model.rois_changed.connect(self._load_initial_data)

    def _load_initial_data(self) -> None:
        self.view.populate_tree(self.model.get_tree_data())

    def _on_import_model(self) -> None:
        models = self.model.list_saved_models()
        model_name = self.view.prompt_model_to_import(models)
        if not model_name:
            return
        if not self.model.load_model(model_name):
            self.view.show_error(f"Nao foi possivel carregar o modelo '{model_name}'.")
            return
        self.view.set_current_model(model_name)

        cameras = self.model.get_cameras()
        if cameras:
            self._show_camera(cameras[0])

    def _on_tree_selection_changed(self, current, previous) -> None:
        if current is None:
            return
        camera = current.text(0) if current.parent() is None else current.parent().text(0)
        self._show_camera(camera)

    def _show_camera(self, camera: str) -> None:
        reference_image = self.model.get_reference_image(camera)
        if reference_image is not None:
            self.view.show_image(reference_image)
        self.view.set_rois(self.model.get_rois(camera))

    def _on_send_clicked(self) -> None:
        if self._inspection_worker is not None and self._inspection_worker.isRunning():
            return

        try:
            threshold = float(self.view.er_field.text().replace(",", "."))
        except ValueError:
            self.view.show_error("Informe um valor numerico valido para ER.")
            return

        cameras = {}
        for index, camera in enumerate(self.model.get_cameras()):
            reference_image = self.model.get_reference_image(camera)
            rois = self.model.get_rois(camera)
            if reference_image is None or not rois:
                continue
            cameras[camera] = {
                "index": index,
                "reference_image": reference_image,
                "rois": rois,
            }

        if not cameras:
            self.view.show_error(
                "Nenhuma camera com ROIs e imagem de referencia configurada. "
                "Importe um modelo primeiro."
            )
            return

        self._current_cameras = cameras
        self.view.set_send_enabled(False)
        self._inspection_worker = InspectionWorker(cameras, threshold)
        self._inspection_worker.camera_captured.connect(self._on_camera_captured)
        self._inspection_worker.finished_ok.connect(self._on_inspection_done)
        self._inspection_worker.error.connect(self._on_inspection_error)
        self._inspection_worker.finished.connect(self._inspection_worker.deleteLater)
        self._inspection_worker.start()

    def _on_camera_captured(self, camera: str, live_image) -> None:
        self.view.show_image(live_image)
        self.view.set_rois(self._current_cameras.get(camera, {}).get("rois", []))

    def _on_inspection_done(self, report: dict) -> None:
        self.view.set_send_enabled(True)
        scores = [
            roi["score"]
            for camera_data in report["cameras"].values()
            for roi in camera_data["rois"]
        ]
        worst_score = min(scores) if scores else None
        self.view.show_result(report["ok"], worst_score)
        self._inspection_worker = None

    def _on_inspection_error(self, message: str) -> None:
        self.view.set_send_enabled(True)
        self.view.show_error(message)
        self._inspection_worker = None
