from PySide6.QtWidgets import QMainWindow, QTabWidget

from src.views.operador_view import OperadorView
from src.views.setup_view import SetupView


class MainView(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setWindowTitle("SimPl")
        self.resize(900, 650)

        self.operador_view = OperadorView()
        self.setup_view = SetupView()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.operador_view, "Operador")
        self.tabs.addTab(self.setup_view, "Setup")

        self.setCentralWidget(self.tabs)
