# Complete example: user CRUD in PySide6 MVC

Minimal working application demonstrating this skill's pattern: `main.py` at the root and MVC layers inside `src/` (UI application, not a distributable package). Use it as a reference for style and architecture — adapt names and fields to the user's domain.

Structure:

```
user-registry/
├── main.py
├── pyproject.toml
└── src/
    ├── models/user_model.py
    ├── views/main_view.py
    └── controllers/main_controller.py
```
(each subfolder with its `__init__.py`)

## src/models/user_model.py

```python
from PySide6.QtCore import QObject, Signal


class UserModel(QObject):
    """Manages the user list and business rules. No Qt Widgets."""

    data_changed = Signal(list)  # emitted whenever the list changes

    def __init__(self):
        super().__init__()
        self._users: list[dict] = []

    def list_all(self) -> list[dict]:
        return list(self._users)

    def add(self, name: str, email: str) -> None:
        name, email = name.strip(), email.strip()
        if not name:
            raise ValueError("Name cannot be empty.")
        if "@" not in email:
            raise ValueError("Invalid email.")
        if any(u["email"] == email for u in self._users):
            raise ValueError("A user with this email already exists.")
        self._users.append({"name": name, "email": email})
        self.data_changed.emit(self.list_all())

    def remove(self, index: int) -> None:
        if 0 <= index < len(self._users):
            del self._users[index]
            self.data_changed.emit(self.list_all())
```

## src/views/main_view.py

```python
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QAbstractItemView,
)


class MainView(QMainWindow):
    """Only builds the interface and exposes widgets. No business logic."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Registry")
        self.resize(520, 400)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Form
        form = QFormLayout()
        self.name_field = QLineEdit()
        self.email_field = QLineEdit()
        form.addRow("Name:", self.name_field)
        form.addRow("Email:", self.email_field)
        layout.addLayout(form)

        # Buttons
        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add")
        self.remove_button = QPushButton("Remove selected")
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        layout.addLayout(buttons)

        # Table
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Name", "Email"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

    # ---- Display helper methods ----
    def update_table(self, users: list[dict]) -> None:
        self.table.setRowCount(len(users))
        for row, user in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(user["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(user["email"]))

    def clear_form(self) -> None:
        self.name_field.clear()
        self.email_field.clear()
        self.name_field.setFocus()

    def selected_row(self) -> int:
        return self.table.currentRow()

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, "Warning", message)
```

## src/controllers/main_controller.py

```python
from PySide6.QtCore import QObject, Slot

from src.models.user_model import UserModel
from src.views.main_view import MainView


class MainController(QObject):
    """Wires View and Model together. Creates no widgets, holds no business rules."""

    def __init__(self, model: UserModel, view: MainView):
        super().__init__()
        self._model = model
        self._view = view
        self._connect_signals()

    def _connect_signals(self):
        self._view.add_button.clicked.connect(self.add_user)
        self._view.remove_button.clicked.connect(self.remove_user)
        self._model.data_changed.connect(self._view.update_table)

    @Slot()
    def add_user(self):
        try:
            self._model.add(
                name=self._view.name_field.text(),
                email=self._view.email_field.text(),
            )
            self._view.clear_form()
        except ValueError as error:
            self._view.show_error(str(error))

    @Slot()
    def remove_user(self):
        index = self._view.selected_row()
        if index < 0:
            self._view.show_error("Select a user in the table.")
            return
        self._model.remove(index)
```

## main.py (project root)

```python
import sys
from PySide6.QtWidgets import QApplication

from src.models.user_model import UserModel
from src.views.main_view import MainView
from src.controllers.main_controller import MainController


def main():
    app = QApplication(sys.argv)
    model = UserModel()
    view = MainView()
    controller = MainController(model=model, view=view)  # keep a live reference
    view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

## pyproject.toml (managed by uv)

```toml
[project]
name = "user-registry"
version = "0.1.0"
description = "User CRUD in PySide6 using the MVC pattern"
requires-python = ">=3.10"
dependencies = [
    "pyside6>=6.6",
]
```

## How to run (uv, not pip)

```bash
uv init user-registry   # if the project doesn't exist yet
cd user-registry
uv add pyside6
uv run main.py
```

## Flow of one event (to explain to the user)

Click "Add" → `MainController.add_user()` → `UserModel.add()` validates and stores → the Model emits `data_changed` → `MainView.update_table()` redraws the table. If validation fails, the controller catches the `ValueError` and calls `MainView.show_error()`.
