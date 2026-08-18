# Long-running operations without freezing the UI (QThread standard)

Read this reference whenever a request involves database access, HTTP/API calls, file processing, hardware/test execution, or anything that can take more than ~100ms. Running these in the controller blocks the Qt event loop and freezes the window.

**This project's single threading standard is `QThread`: subclass it and override `run()`.** Do not introduce `QThreadPool`/`QRunnable`, `concurrent.futures`, or raw `threading.Thread` — one pattern across the whole codebase.

## The iron rules

1. **Never touch widgets from inside `run()`.** Qt widgets are not thread-safe; only the main thread may call View methods. Everything leaving the thread goes through signals — Qt delivers cross-thread signals safely as queued events, so the connected slots run on the main thread.
2. **Workers are generic and self-contained.** They receive plain data in `__init__` (a serial number, a path, a config dict — never View or widget references) and do the work inside `run()`, calling whatever functions they need. They do NOT require a Model: injecting one is optional, only when the heavy logic already lives there.
3. **The controller keeps a reference to the worker** (`self._worker`) — a local variable gets garbage-collected and the thread dies mid-flight.

## Worker template (one-shot task)

Declare the signals the task needs as class attributes, receive plain parameters, and do the work in `run()`:

```python
# src/workers/report_worker.py  (or src/utils/workers.py for small projects)
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class ReportWorker(QThread):
    """Generates the report outside the UI thread."""

    finished_ok = Signal(object)   # emits the result (don't shadow QThread.finished)
    error = Signal(str)

    def __init__(self, source_dir: Path, month: int, parent=None):
        super().__init__(parent)
        self._source_dir = source_dir
        self._month = month

    def run(self):
        try:
            result = build_report(self._source_dir, self._month)  # any function/service
        except Exception as e:
            self.error.emit(str(e))
        else:
            self.finished_ok.emit(result)
```

For fully generic one-liners, a reusable wrapper that runs ANY callable also fits the standard:

```python
# src/utils/workers.py
from PySide6.QtCore import QThread, Signal


class FunctionWorker(QThread):
    """Runs any callable in a thread: FunctionWorker(fn, arg1, kw=value)."""

    finished_ok = Signal(object)
    error = Signal(str)

    def __init__(self, fn, *args, parent=None, **kwargs):
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as e:
            self.error.emit(str(e))
        else:
            self.finished_ok.emit(result)
```

Use a dedicated worker class (like `ReportWorker`) when the task has its own signals, steps, or state; use `FunctionWorker` for simple "run this function off the UI thread" cases.

Controller using it:

```python
from PySide6.QtCore import QObject, Slot

from src.workers.report_worker import ReportWorker


class MainController(QObject):
    def __init__(self, model, view):
        super().__init__()
        self._model = model
        self._view = view
        self._worker = None
        self._connect_signals()

    def _connect_signals(self):
        self._view.report_button.clicked.connect(self.generate_report)

    @Slot()
    def generate_report(self):
        if self._worker is not None and self._worker.isRunning():
            return                                        # prevent double start
        self._view.report_button.setEnabled(False)
        self._view.show_loading(True)

        self._worker = ReportWorker(RESULTS_DIR, month=7, parent=self)
        self._worker.finished_ok.connect(self._on_report_ready)
        self._worker.error.connect(self._on_report_error)
        self._worker.finished.connect(self._worker.deleteLater)  # cleanup
        self._worker.start()

    @Slot(object)
    def _on_report_ready(self, report):                   # runs on the MAIN thread
        self._view.show_loading(False)
        self._view.report_button.setEnabled(True)
        self._view.show_report(report)

    @Slot(str)
    def _on_report_error(self, message):
        self._view.show_loading(False)
        self._view.report_button.setEnabled(True)
        self._view.show_error(message)
```

Flow: disable the trigger, start the worker, and both handlers re-enable the UI. `finished` (built into `QThread`) is connected to `deleteLater` so the object is disposed after the run.

## Continuous / cancellable task

For loops (polling, monitoring, batch processing), use Qt's built-in interruption flag instead of a custom boolean:

```python
from PySide6.QtCore import QThread, Signal


class MonitorWorker(QThread):
    reading = Signal(dict)
    stopped = Signal()

    def __init__(self, port: str, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self._port = port
        self._interval_ms = interval_ms

    def run(self):
        while not self.isInterruptionRequested():
            self.reading.emit(read_sensor(self._port))   # any function/service
            self.msleep(self._interval_ms)               # QThread.msleep — safe inside run()
        self.stopped.emit()
```

Controller stops it gracefully (e.g., on window close):

```python
def stop_monitor(self):
    if self._worker is not None and self._worker.isRunning():
        self._worker.requestInterruption()
        self._worker.wait(5000)               # block briefly until run() returns
```

Never call `terminate()` — it kills the thread at an arbitrary point and corrupts state. Always `requestInterruption()` + `wait()`.

## Where workers live

- `src/workers/` (with `__init__.py`) when the project has several; `src/utils/workers.py` is fine for one or two.
- Signals belong on the worker class itself (as above). For app-wide events that many screens observe (logging, global status), a shared `QObject` hub in `utils/` (e.g., a `reporter` with `log = Signal(str)`) is acceptable — the controller connects the hub's signals to the View; workers emit into the hub. Even then, workers never touch widgets.

## Pitfalls checklist

- Calling any `self._view...` method inside `run()` → crash or silent corruption. Only connected slots (main thread) touch the View.
- Naming a custom signal `finished` → shadows `QThread.finished` and breaks cleanup. Use `finished_ok`, `done`, `result_ready`.
- Not keeping `self._worker` as an attribute → garbage collection kills the thread mid-run.
- Not guarding against double start → two workers race. Check `isRunning()` and/or disable the trigger button.
- `sqlite3` connections cannot cross threads → open the connection inside `run()` (or have the Model create one per thread).
- App closing while a thread runs → on shutdown, `requestInterruption()` + `wait()` for continuous workers; for one-shot workers, either `wait()` or let them finish before closing.
