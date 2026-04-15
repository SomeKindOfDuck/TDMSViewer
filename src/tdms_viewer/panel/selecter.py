from PyQt6 import QtCore, QtWidgets


class ColumnSelectDialog(QtWidgets.QDialog):
    """
    Checkbox list dialog to choose columns.
    """
    def __init__(self, columns: list[str], title="Select items", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(420, 520)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        self.btn_all = QtWidgets.QPushButton("All")
        self.btn_none = QtWidgets.QPushButton("None")
        self.btn_all.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_none.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        top.addWidget(self.btn_all)
        top.addWidget(self.btn_none)
        top.addStretch(1)
        outer.addLayout(top)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        outer.addWidget(scroll, 1)

        inner = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        scroll.setWidget(inner)

        self.checks = {}
        for c in columns:
            cb = QtWidgets.QCheckBox(str(c))
            self.checks[c] = cb
            lay.addWidget(cb)

        lay.addStretch(1)

        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        outer.addWidget(btns)

        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        self.btn_all.clicked.connect(self._select_all)
        self.btn_none.clicked.connect(self._select_none)

    def _select_all(self):
        for cb in self.checks.values():
            cb.setChecked(True)

    def _select_none(self):
        for cb in self.checks.values():
            cb.setChecked(False)

    def selected(self) -> list[str]:
        return [c for c, cb in self.checks.items() if cb.isChecked()]
