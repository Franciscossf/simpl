from src.models.inspection_model import InspectionModel
from src.views.setup_view import SetupView
from src.workers.camera_worker import CameraWorker


class SetupController:
    def __init__(self, model: InspectionModel, view: SetupView) -> None:
        self.model = model
        self.view = view
        self._camera_worker: CameraWorker | None = None
        self._current_camera: str | None = None
        self._last_model_name: str | None = None
        self._connect_signals()
        self._load_cameras()

    def _connect_signals(self) -> None:
        self.view.camera_selector.currentTextChanged.connect(self._on_camera_changed)
        self.view.add_roi_button.clicked.connect(self._on_add_roi)
        self.view.remove_roi_button.clicked.connect(self._on_remove_roi)
        self.view.import_button.clicked.connect(self._on_import)
        self.view.save_button.clicked.connect(self._on_save)
        self.view.add_reference_button.clicked.connect(self._on_add_reference)
        self.view.remove_reference_button.clicked.connect(self._on_remove_reference)
        self.view.remove_all_references_button.clicked.connect(
            self._on_remove_all_references
        )
        self.view.toggle_camera_button.clicked.connect(self._on_toggle_camera)
        self.view.roi_list.currentItemChanged.connect(self._on_roi_selected)
        self.view.threshold_spinbox.valueChanged.connect(self._on_threshold_changed)
        self.view.autofocus_checkbox.toggled.connect(self._on_autofocus_toggled)
        self.view.focus_slider.valueChanged.connect(self._on_focus_changed)

    def _load_cameras(self) -> None:
        self.view.set_cameras(self.model.get_cameras())

    def _on_camera_changed(self, camera: str) -> None:
        self._commit_current_camera_rois()
        self._current_camera = camera
        self._refresh_current_camera_view()

    def _refresh_current_camera_view(self) -> None:
        self.view.clear_rois()
        self.view.clear_frame()
        self.view.clear_references()
        if not self._current_camera:
            return

        reference_images = self.model.get_reference_images(self._current_camera)
        self.view.set_reference_images(reference_images)
        if reference_images:
            self.view.show_frame(reference_images[-1])

        for roi in self.model.get_rois(self._current_camera):
            self.view.add_roi_item(
                roi["name"],
                roi["x"],
                roi["y"],
                roi["w"],
                roi["h"],
                roi.get("angle", 0.0),
                roi.get("threshold", 80.0),
            )

    def _commit_current_camera_rois(self) -> None:
        if not self._current_camera:
            return
        self.model.set_rois(self._current_camera, self.view.get_rois_geometry())
        self.model.set_reference_images(
            self._current_camera, self.view.get_reference_images()
        )

    def _on_add_reference(self) -> None:
        frame = self.view.get_current_frame()
        if frame is None:
            self.view.show_camera_error(
                "Nenhuma imagem capturada para usar como referencia."
            )
            return
        self.view.add_reference_image(frame)

    def _on_remove_reference(self) -> None:
        index = self.view.selected_reference_index()
        if index is not None:
            self.view.remove_reference_image(index)

    def _on_remove_all_references(self) -> None:
        if not self.view.get_reference_images():
            return
        if self.view.confirm_remove_all_references():
            self.view.clear_references()

    def _on_add_roi(self) -> None:
        name = self.view.prompt_roi_name()
        if name:
            self.view.add_roi_item(name)

    def _on_remove_roi(self) -> None:
        name = self.view.selected_roi_name()
        if name:
            self.view.remove_roi_item(name)

    def _on_roi_selected(self, current, previous) -> None:
        name = current.text() if current is not None else None
        self.view.highlight_roi(name)
        self.view.show_roi_threshold(self.view.get_roi_threshold(name) if name else None)

    def _on_threshold_changed(self, value: float) -> None:
        name = self.view.selected_roi_name()
        if name:
            self.view.set_roi_threshold(name, value)

    def _on_autofocus_toggled(self, enabled: bool) -> None:
        connected = self._camera_worker is not None and self._camera_worker.isRunning()
        self.view.set_focus_slider_enabled(connected and not enabled)
        if self._camera_worker is not None:
            self._camera_worker.request_autofocus(enabled)

    def _on_focus_changed(self, value: int) -> None:
        if self._camera_worker is not None:
            self._camera_worker.request_focus(value)

    def _on_save(self) -> None:
        self._commit_current_camera_rois()

        cameras_missing_reference = [
            camera
            for camera in self.model.get_cameras()
            if self.model.get_rois(camera) and not self.model.get_reference_images(camera)
        ]
        if cameras_missing_reference:
            self.view.show_save_error(
                "Adicione ao menos uma referencia para: "
                + ", ".join(cameras_missing_reference)
            )
            return

        model_name = self.view.prompt_model_name(default=self._last_model_name or "")
        if not model_name:
            return
        if not self.view.confirm_save(model_name):
            return

        self.model.save_model(model_name)
        self._last_model_name = model_name
        self.view.show_saved_message(model_name)

    def _on_import(self) -> None:
        models = self.model.list_saved_models()
        model_name = self.view.prompt_model_to_import(models)
        if not model_name:
            return
        if not self.model.load_model(model_name):
            self.view.show_camera_error(f"Nao foi possivel carregar o modelo '{model_name}'.")
            return

        self._last_model_name = model_name
        self._refresh_current_camera_view()
        self.view.show_imported_message(model_name)

    def _on_toggle_camera(self) -> None:
        if self._camera_worker is not None and self._camera_worker.isRunning():
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self) -> None:
        camera_index = self.view.camera_selector.currentIndex()
        if camera_index < 0:
            return
        self._camera_worker = CameraWorker(camera_index)
        self._camera_worker.frame_ready.connect(self.view.show_frame)
        self._camera_worker.error.connect(self._on_camera_error)
        self._camera_worker.finished.connect(self._camera_worker.deleteLater)
        self._camera_worker.start()
        self.view.set_camera_connected(True)

        autofocus_enabled = self.view.autofocus_checkbox.isChecked()
        self._camera_worker.request_autofocus(autofocus_enabled)
        if not autofocus_enabled:
            self._camera_worker.request_focus(self.view.focus_slider.value())

    def _stop_camera(self) -> None:
        if self._camera_worker is not None:
            self._camera_worker.requestInterruption()
            self._camera_worker.wait(2000)
            self._camera_worker = None
        self.view.set_camera_connected(False)

    def _on_camera_error(self, message: str) -> None:
        self.view.show_camera_error(message)
        self._camera_worker = None
        self.view.set_camera_connected(False)

    def shutdown(self) -> None:
        if self._camera_worker is not None and self._camera_worker.isRunning():
            self._stop_camera()
