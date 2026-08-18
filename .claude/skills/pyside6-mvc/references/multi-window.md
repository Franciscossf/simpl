# Multiple windows, dialogs, and shared Models

Read this reference when the app has more than one screen: extra windows, edit/detail dialogs, wizards, or settings screens.

## Core principles

1. **One View, one Controller.** Every non-trivial window or dialog gets its own MVC trio (dialogs may reuse an existing Model).
2. **The Model is shared, not duplicated.** Screens that show the same data receive the SAME Model instance, injected from `main.py` (or from a parent controller). Because the Model emits signals (`data_changed`), every connected View updates automatically — this is what keeps screens in sync for free.
3. **Controllers open screens; Views never do.** A button click reaches the controller, and the controller creates/opens the next dialog or window. Views don't know other Views exist.

## Modal dialog (the common case: add/edit forms)

Dialog View — dumb as always, plus a convenience method to read the form:

```python
# src/views/user_dialog.py
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox


class UserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New User")
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        self.name_field = QLineEdit()
        self.email_field = QLineEdit()
        layout.addRow("Name:", self.name_field)
        layout.addRow("Email:", self.email_field)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def form_data(self) -> dict:
        return {"name": self.name_field.text(), "email": self.email_field.text()}
```

Main controller opening it and applying the result to the shared Model:

```python
# inside MainController
from src.views.user_dialog import UserDialog

@Slot()
def open_new_user_dialog(self):
    dialog = UserDialog(parent=self._view)
    if dialog.exec():                      # modal; blocks until Ok/Cancel
        data = dialog.form_data()
        try:
            self._model.add(**data)        # model emits data_changed → table updates
        except ValueError as error:
            self._view.show_error(str(error))
```

For simple form dialogs this is enough — no dedicated controller needed. Give the dialog its own controller when it has real behavior (validation while typing, internal lists, async loading).

## Second full window sharing the same Model

`main.py` (or a top-level `AppController`) owns the shared instances and wires each screen:

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication

from src.models.user_model import UserModel
from src.views.main_view import MainView
from src.views.stats_view import StatsView
from src.controllers.main_controller import MainController
from src.controllers.stats_controller import StatsController


def main():
    app = QApplication(sys.argv)

    user_model = UserModel()                       # ONE instance...

    main_view = MainView()
    main_controller = MainController(model=user_model, view=main_view)

    stats_view = StatsView()
    stats_controller = StatsController(model=user_model, view=stats_view)  # ...shared

    main_view.show()
    stats_view.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

Both controllers connect `user_model.data_changed` to their own View. Adding a user in the main window updates the stats window with zero extra wiring — that is the payoff of constructor injection plus Model signals.

If the second window is opened on demand instead of at startup, the main controller creates it lazily and keeps a reference:

```python
@Slot()
def open_stats(self):
    if self._stats_controller is None:             # create once, reuse after
        view = StatsView()
        self._stats_controller = StatsController(model=self._model, view=view)
    self._stats_controller.view.show()
    self._stats_controller.view.raise_()           # bring to front if already open
```

(Expose the view on the child controller as a read-only property for this.)

## Communication between controllers

- **Default channel: the shared Model.** Controller A changes the Model; the Model's signal reaches Controller B's View. Most "how do I tell the other screen?" questions are solved this way — no direct coupling.
- **UI-only coordination** (e.g., "open screen X"): the parent controller that created both children calls the child's method, or children expose their own signals the parent connects. Children never import each other.
- Growing app: promote `main.py`'s wiring into an `AppController` (in `controllers/`) that owns shared Models and child controllers. `main.py` shrinks back to creating `QApplication` + `AppController`.

## Pitfalls checklist

- Creating a second `UserModel()` for the second screen → screens silently drift apart. Share the instance.
- Opening a dialog from inside the View → the View now knows about navigation; move it to the controller.
- Not keeping a reference to a non-modal window/controller → it is garbage-collected and closes instantly.
- Passing `parent=self._view` to dialogs is good practice: correct centering, taskbar behavior, and cleanup.
