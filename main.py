import sys

import pyqtgraph as pg
from PySide6.QtWidgets import QApplication

from src.controllers.operador_controller import OperadorController
from src.controllers.setup_controller import SetupController
from src.models.inspection_model import InspectionModel
from src.views.main_view import MainView
import qdarktheme


def main():
    pg.setConfigOptions(imageAxisOrder="row-major")
    app = QApplication(sys.argv)
    qdarktheme.setup_theme(custom_colors={"primary": "#D71ABE"},
                           theme="light")

    model = InspectionModel()
    view = MainView()

    operador_controller = OperadorController(model=model, view=view.operador_view)
    setup_controller = SetupController(model=model, view=view.setup_view)
    app.aboutToQuit.connect(setup_controller.shutdown)

    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
