from PySide6.QtCore import Signal
from PySide6.QtWidgets import QMainWindow, QTabWidget

from src.views.operador_view import OperadorView
from src.views.setup_view import SetupView


class MainView(QMainWindow):
    operador_tab_activated = Signal()

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
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)

    def _on_tab_changed(self, index: int) -> None:
        if self.tabs.widget(index) is self.operador_view:
            self.operador_tab_activated.emit()
