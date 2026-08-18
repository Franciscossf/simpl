from src.models.inspection_model import InspectionModel
from src.views.operador_view import OperadorView


class OperadorController:
    def __init__(self, model: InspectionModel, view: OperadorView) -> None:
        self.model = model
        self.view = view
        self._connect_signals()
        self._load_initial_data()

    def _connect_signals(self) -> None:
        self.view.send_button.clicked.connect(self._on_send_clicked)
        self.model.rois_changed.connect(self._load_initial_data)

    def _load_initial_data(self) -> None:
        self.view.populate_tree(self.model.get_tree_data())

    def _on_send_clicked(self) -> None:
        er_value = self.view.er_field.text()
        self.model.submit_er(er_value)
