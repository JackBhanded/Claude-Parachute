"""app.py — the double-click Claude Parachute window.

Thin paint over the tested :mod:`appmodel`. Qt is imported lazily inside
``main()`` so importing this module never requires PySide6 (the shipped .exe
bundles it). If PySide6 is missing, ``main()`` explains how to get it.

The window's one big idea: a calm list of checkpoints and a single, obvious
"Pull the cord" button that restores the selected one — undoably.
"""

from __future__ import annotations

import sys
import webbrowser

from .appmodel import ParachuteModel
from .dashboard import _claude_logo_svg, write_dashboard

_CREAM = "#F4EEE4"
_CARD = "#FBF8F2"
_INK = "#2B2722"
_MUTED = "#8A8178"
_ORANGE = "#D97757"
_LINE = "#E7DFD2"
_OK = "#3F8F77"
_IDLE = "#B8AFA3"

_QSS = f"""
QWidget {{ background: {_CREAM}; color: {_INK};
  font-family: 'Segoe UI', -apple-system, Roboto, Arial; font-size: 13px; }}
QLabel#title {{ font-size: 20px; font-weight: 600; }}
QLabel#sub {{ color: {_MUTED}; font-size: 12px; }}
QLabel#section {{ color: {_MUTED}; font-size: 11px; font-weight: 600; }}
QLabel#headline {{ color: {_OK}; font-weight: 600; }}
QFrame#card {{ background: {_CARD}; border: 1px solid {_LINE}; border-radius: 12px; }}
QFrame#stat {{ background: {_CARD}; border: 1px solid {_LINE}; border-radius: 12px; }}
QLabel#statnum {{ color: {_ORANGE}; font-size: 20px; font-weight: 600; }}
QLabel#statlbl {{ color: {_MUTED}; font-size: 10px; }}
QPushButton {{ background: {_CARD}; border: 1px solid {_LINE}; border-radius: 9px;
  padding: 7px 14px; }}
QPushButton:hover {{ background: #fff; }}
QPushButton#primary {{ background: {_ORANGE}; color: white; border: none; font-weight: 600;
  padding: 9px 18px; font-size: 14px; }}
QPushButton#primary:hover {{ background: #c8633f; }}
QPushButton#small {{ padding: 3px 10px; }}
QListWidget {{ background: {_CARD}; border: 1px solid {_LINE}; border-radius: 12px;
  padding: 4px; }}
QListWidget::item {{ padding: 8px 10px; border-radius: 8px; }}
QListWidget::item:selected {{ background: {_ORANGE}; color: white; }}
QScrollArea {{ border: none; }}
QCheckBox {{ color: {_INK}; }}
"""


def _missing_pyside_message() -> str:
    return (
        "Claude Parachute's window needs PySide6.\n\n"
        "Install it with:\n    pip install --user PySide6\n\n"
        "Or use the command line instead:\n"
        "    python -m claude_parachute status\n"
    )


def _make_tray_icon():
    """Build a QIcon from the Claude logo (rendered SVG), with a dot fallback."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    try:
        from PySide6.QtCore import QByteArray
        from PySide6.QtSvg import QSvgRenderer
        r = QSvgRenderer(QByteArray(_claude_logo_svg(64).encode("utf-8")))
        p = QPainter(pm)
        r.render(p)
        p.end()
    except Exception:
        from PySide6.QtGui import QColor
        p = QPainter(pm)
        p.setBrush(QColor(_ORANGE))
        p.setPen(Qt.NoPen)
        p.drawEllipse(8, 8, 48, 48)
        p.end()
    return QIcon(pm)


def main(start_in_tray: bool = False) -> int:
    try:
        from PySide6.QtWidgets import (
            QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QListWidget,
            QListWidgetItem, QMenu, QMessageBox, QPushButton, QSystemTrayIcon,
            QVBoxLayout, QWidget,
        )
    except ImportError:
        sys.stderr.write(_missing_pyside_message())
        return 1
    try:
        from PySide6.QtSvgWidgets import QSvgWidget
        _have_svg = True
    except ImportError:
        _have_svg = False

    model = ParachuteModel()

    class ParachuteWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Claude Parachute")
            self.setMinimumSize(540, 640)
            self.setStyleSheet(_QSS)
            self._tray = None
            self._build()
            self.refresh()

        def closeEvent(self, event):
            if self._tray is not None and self._tray.isVisible():
                event.ignore()
                self.hide()
                try:
                    self._tray.showMessage(
                        "Claude Parachute",
                        "Still here in your tray — your safety net stays armed.")
                except Exception:
                    pass
            else:
                event.accept()

        def _build(self):
            root = QVBoxLayout(self)
            root.setContentsMargins(22, 20, 22, 18)
            root.setSpacing(12)

            header = QHBoxLayout()
            if _have_svg:
                logo = QSvgWidget()
                logo.load(_claude_logo_svg(30).encode("utf-8"))
                logo.setFixedSize(30, 30)
                header.addWidget(logo)
            titles = QVBoxLayout(); titles.setSpacing(0)
            t = QLabel("Claude Parachute"); t.setObjectName("title")
            sub = QLabel("The safety net for when /rewind can't save you.")
            sub.setObjectName("sub")
            titles.addWidget(t); titles.addWidget(sub)
            header.addLayout(titles); header.addStretch(1)
            root.addLayout(header)

            self._headline = QLabel(""); self._headline.setObjectName("headline")
            root.addWidget(self._headline)

            # Stat chips
            self._stats_row = QHBoxLayout(); self._stats_row.setSpacing(8)
            root.addLayout(self._stats_row)

            self._section_lbl = QLabel("SNAPSHOT TIMELINE")
            self._section_lbl.setObjectName("section")
            root.addWidget(self._section_lbl)

            self._list = QListWidget()
            self._list.itemDoubleClicked.connect(lambda _i: self._pull_cord())
            root.addWidget(self._list, 1)

            self._status = QLabel(""); self._status.setObjectName("sub")
            self._status.setWordWrap(True)
            root.addWidget(self._status)

            # Auto-snap toggle
            self._autosnap = QCheckBox("Auto-snapshot after every tool (Bash included)")
            self._autosnap.toggled.connect(self._toggle_autosnap)
            root.addWidget(self._autosnap)

            actions = QHBoxLayout()
            snap_btn = QPushButton("Snapshot now")
            snap_btn.clicked.connect(self._snapshot_now)
            dash_btn = QPushButton("Open dashboard")
            dash_btn.clicked.connect(self._open_dashboard)
            self._cord_btn = QPushButton("Pull the cord (restore)")
            self._cord_btn.setObjectName("primary")
            self._cord_btn.clicked.connect(self._pull_cord)
            actions.addWidget(snap_btn)
            actions.addWidget(dash_btn)
            actions.addStretch(1)
            actions.addWidget(self._cord_btn)
            root.addLayout(actions)

        def _clear_stats(self):
            while self._stats_row.count():
                it = self._stats_row.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()

        def _stat(self, num, lbl):
            f = QFrame(); f.setObjectName("stat")
            lay = QVBoxLayout(f); lay.setContentsMargins(10, 8, 10, 8); lay.setSpacing(0)
            n = QLabel(str(num)); n.setObjectName("statnum")
            from PySide6.QtCore import Qt
            n.setAlignment(Qt.AlignCenter)
            l = QLabel(lbl); l.setObjectName("statlbl"); l.setAlignment(Qt.AlignCenter)
            lay.addWidget(n); lay.addWidget(l)
            self._stats_row.addWidget(f)

        def refresh(self):
            snap = model.build_snapshot()
            self._snap = snap

            self._headline.setText(snap.headline)
            self._clear_stats()
            self._stat(snap.count, "SNAPSHOTS")
            self._stat(snap.size_mb, "MB USED")
            self._stat("On" if snap.hooks_on else "Off", "AUTO-SNAP")
            self._stat("Yes" if snap.armed else "No", "ARMED")

            self._list.clear()
            for r in snap.rows:
                from PySide6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(f"[{r.index}]  {r.label}\n        {r.short} · {r.when}")
                self._list.addItem(item)
            if snap.rows:
                self._list.setCurrentRow(0)

            # Auto-snap checkbox without re-firing the toggle handler.
            self._autosnap.blockSignals(True)
            self._autosnap.setChecked(snap.hooks_on)
            self._autosnap.setEnabled(snap.git_ok)
            self._autosnap.blockSignals(False)

            armed_ok = snap.armed and bool(snap.rows)
            self._cord_btn.setEnabled(armed_ok)
            if not snap.git_ok:
                self._status.setText("git isn't installed. Parachute needs it — "
                                     "grab it from git-scm.com/download/win.")
            elif not snap.armed:
                self._status.setText("Not armed in this project yet. Use Snapshot now "
                                     "to arm it and take your first checkpoint.")
            else:
                self._status.setText(f"Watching {snap.project}")

        def _selected_index(self):
            row = self._list.currentRow()
            if 0 <= row < len(self._snap.rows):
                return self._snap.rows[row].index
            return None

        # -- actions -- #
        def _snapshot_now(self):
            if not self._snap.armed:
                if not model.arm():
                    self._status.setText(model.last_message)
                    return
            model.take_snapshot("manual checkpoint")
            self._status.setText(model.last_message)
            self.refresh()

        def _pull_cord(self):
            idx = self._selected_index()
            if idx is None:
                self._status.setText("Pick a checkpoint in the list first.")
                return
            row = self._snap.rows[idx - 1]
            from PySide6.QtWidgets import QMessageBox
            box = QMessageBox(self)
            box.setWindowTitle("Pull the cord?")
            box.setText(f"Restore your project to:\n\n[{row.index}] {row.label}\n{row.short} · {row.when}")
            box.setInformativeText("Don't worry — Parachute takes a safety snapshot of "
                                   "right-now first, so you can undo this.")
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            box.setDefaultButton(QMessageBox.Cancel)
            if box.exec() != QMessageBox.Yes:
                return
            model.restore(str(idx))
            self._status.setText(model.last_message)
            self.refresh()

        def _toggle_autosnap(self, on):
            model.set_hooks(bool(on))
            self._status.setText(model.last_message)
            self.refresh()

        def _open_dashboard(self):
            if not self._snap.armed:
                self._status.setText("Arm Parachute first (Snapshot now), then open the dashboard.")
                return
            out = write_dashboard(model.repo)
            try:
                webbrowser.open(out.as_uri())
            except Exception:
                pass
            self._status.setText(f"Dashboard: {out}")

    app = QApplication.instance() or QApplication(sys.argv)
    win = ParachuteWindow()

    if QSystemTrayIcon.isSystemTrayAvailable():
        from PySide6.QtGui import QAction
        app.setQuitOnLastWindowClosed(False)

        def _show():
            win.showNormal(); win.raise_(); win.activateWindow()

        tray = QSystemTrayIcon(_make_tray_icon())
        tray.setToolTip("Claude Parachute")
        menu = QMenu()
        a_open = QAction("Open Parachute", menu); a_open.triggered.connect(_show)
        a_snap = QAction("Snapshot now", menu); a_snap.triggered.connect(win._snapshot_now)
        a_dash = QAction("Open dashboard", menu); a_dash.triggered.connect(win._open_dashboard)
        a_quit = QAction("Quit", menu); a_quit.triggered.connect(app.quit)
        for a in (a_open, a_snap, a_dash):
            menu.addAction(a)
        menu.addSeparator(); menu.addAction(a_quit)
        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda reason: _show() if reason == QSystemTrayIcon.DoubleClick else None)
        tray.show()
        win._tray = tray
        if not start_in_tray:
            win.show()
    else:
        win.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
