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

from . import startup
from .appmodel import ParachuteModel
from .dashboard import _claude_logo_svg, write_dashboard

# Kept for the tray-glyph fill + any legacy refs.
_ORANGE = "#C8632F"

# --- the fleet's elevated-brew look, tuned for Qt, with a sleek dark mode. ----
_LIGHT = {
    "bg": "#F4EFE6", "ink": "#1C1712", "muted": "#5F564B", "orange": "#C8632F",
    "orange2": "#E0875C", "ok": "#2E7D63", "line": "#E4DBCC", "qcardbg": "#FBF1E9",
    "accentline": "#EAC3AC", "btn": "#FBF6EE", "btnhover": "#FFFFFF",
    "listbg": "#FCF8F2", "scroll": "#D9CFBE", "shadow_a": 46,
}
_DARK = {
    "bg": "#17120E", "ink": "#F7F1E7", "muted": "#B7AEA2", "orange": "#E0875C",
    "orange2": "#EE9E75", "ok": "#4FB592", "line": "#3A322A", "qcardbg": "#2E2018",
    "accentline": "#7A4F36", "btn": "#241D16", "btnhover": "#312820",
    "listbg": "#241D16", "scroll": "#43392F", "shadow_a": 150,
}


def _qss(dark: bool) -> str:
    c = _DARK if dark else _LIGHT
    grad = (f"qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {c['orange2']}, "
            f"stop:1 {c['orange']})")
    return f"""
QWidget {{ background: {c['bg']}; color: {c['ink']};
  font-family: 'Segoe UI', -apple-system, Roboto, Arial; font-size: 13px; }}
QLabel#title {{ font-size: 22px; font-weight: 700; color: {c['ink']}; }}
QLabel#sub {{ color: {c['muted']}; font-size: 12px; }}
QLabel#section {{ color: {c['muted']}; font-size: 11px; font-weight: 700; }}
QLabel#headline {{ color: {c['ok']}; font-weight: 700; font-size: 14px; }}
QFrame#card {{ background: transparent; border: 1px solid {c['line']}; border-radius: 14px; }}
QFrame#stat {{ background: transparent; border: 1px solid {c['accentline']}; border-radius: 12px; }}
QLabel#statnum {{ color: {c['orange']}; font-size: 20px; font-weight: 700; }}
QLabel#statlbl {{ color: {c['muted']}; font-size: 10px; font-weight: 700; }}
QPushButton {{ background: {c['btn']}; border: 1px solid {c['line']}; border-radius: 10px;
  padding: 7px 14px; color: {c['ink']}; }}
QPushButton:hover {{ background: {c['btnhover']}; border-color: {c['orange']}; }}
QPushButton#primary {{ background: {grad}; color: white; border: none; font-weight: 700;
  padding: 9px 18px; font-size: 14px; }}
QPushButton#primary:hover {{ background: {c['orange']}; }}
QPushButton#small {{ padding: 3px 10px; border-radius: 8px; }}
QPushButton#toggle {{ background: {c['btn']}; border: 1px solid {c['line']}; border-radius: 10px;
  padding: 7px 14px; color: {c['muted']}; font-weight: 600; }}
QPushButton#toggle:hover {{ color: {c['ink']}; border-color: {c['orange']}; background: {c['btnhover']}; }}
QListWidget {{ background: {c['listbg']}; border: 1px solid {c['line']}; border-radius: 14px;
  padding: 5px; }}
QListWidget::item {{ padding: 9px 11px; border-radius: 9px; color: {c['ink']}; }}
QListWidget::item:selected {{ background: {grad}; color: white; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {c['scroll']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {c['muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QCheckBox {{ color: {c['ink']}; spacing: 8px; }}
"""


def _missing_pyside_message() -> str:
    return (
        "Claude Parachute's window needs PySide6.\n\n"
        "Install it with:\n    pip install --user PySide6\n\n"
        "Or use the command line instead:\n"
        "    python -m claude_parachute status\n"
    )


def _parachute_tray_svg(size=64):
    """A clean little parachute glyph in Claude's orange. The tray icon uses this
    (rather than the Claude logo) so Parachute is easy to tell apart from the
    other fleet tools at a glance — they'd otherwise all show the same asterisk.
    The Claude logo stays the brand mark in the window header and the README."""
    o = _ORANGE
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><title>Parachute</title>'
        # canopy: a dome with three scallops along the bottom edge
        f'<path d="M3 11 a9 8 0 0 1 18 0 a3 2.4 0 0 1 -6 0 a3 2.4 0 0 1 -6 0 '
        f'a3 2.4 0 0 1 -6 0 z" fill="{o}"/>'
        # rigging lines converging to the harness
        f'<path d="M4.2 11.4 L11.3 16.4 M12 11.6 L12 16.4 M19.8 11.4 L12.7 16.4" '
        f'stroke="{o}" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
        # the little harness/payload
        f'<path d="M10.7 16.4 h2.6 l-.5 3.1 a0.8 0.8 0 0 1 -1.6 0 z" fill="{o}"/>'
        f'</svg>'
    )


def _make_tray_icon():
    """Build the tray QIcon from the parachute glyph (rendered SVG), with a dot
    fallback if SVG rendering isn't available."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    try:
        from PySide6.QtCore import QByteArray
        from PySide6.QtSvg import QSvgRenderer
        r = QSvgRenderer(QByteArray(_parachute_tray_svg(64).encode("utf-8")))
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

    # Self-heal on launch: drop any of our hooks whose exe has gone missing
    # (e.g. an old build you ran from Downloads then moved). Never fatal.
    try:
        from .hookconfig import claude_code_home, prune_stale_hooks
        prune_stale_hooks(claude_code_home())
    except Exception:
        pass

    class ParachuteWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Claude Parachute")
            self.setMinimumSize(680, 680)
            self.resize(720, 740)
            from PySide6.QtCore import QSettings
            self._settings = QSettings("Jack", "ClaudeParachute")
            self._dark = self._settings.value("dark", False, type=bool)
            self.setStyleSheet(_qss(self._dark))
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
            from PySide6.QtCore import Qt
            self._theme_btn = QPushButton("Light" if self._dark else "Dark")
            self._theme_btn.setObjectName("toggle")
            self._theme_btn.setCursor(Qt.PointingHandCursor)
            self._theme_btn.clicked.connect(self._toggle_theme)
            header.addWidget(self._theme_btn)
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
            self._apply_shadow(self._list, blur=26, dy=7)

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

        def _apply_shadow(self, w, blur=24, dy=6):
            try:
                from PySide6.QtGui import QColor
                from PySide6.QtWidgets import QGraphicsDropShadowEffect
                eff = QGraphicsDropShadowEffect(self)
                eff.setBlurRadius(blur); eff.setXOffset(0); eff.setYOffset(dy)
                a = (_DARK if self._dark else _LIGHT)["shadow_a"]
                eff.setColor(QColor(0, 0, 0, a))
                w.setGraphicsEffect(eff)
            except Exception:
                pass

        def _toggle_theme(self):
            self._dark = not self._dark
            try:
                self._settings.setValue("dark", self._dark)
            except Exception:
                pass
            self.setStyleSheet(_qss(self._dark))
            self._theme_btn.setText("Light" if self._dark else "Dark")

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

    # Single-instance guard: if a Parachute window is already running, don't open
    # a second one — just bow out quietly. (Belt-and-braces against anything that
    # might launch the app more than once.)
    try:
        from PySide6.QtCore import QSharedMemory
        _lock = QSharedMemory("ClaudeParachuteSingleInstance")
        if not _lock.create(1):
            return 0
        app._parachute_lock = _lock   # keep it alive for the process lifetime
    except Exception:
        pass

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

        # Start with Windows (per-user, no admin). Only meaningful for the
        # packaged .exe, so it's greyed out when running from source.
        a_startup = QAction("Run at startup", menu)
        a_startup.setCheckable(True)
        a_startup.setChecked(startup.is_enabled())
        a_startup.setEnabled(startup.is_frozen())

        def _toggle_startup(checked: bool) -> None:
            ok = startup.enable() if checked else startup.disable()
            if not ok:                       # registry wrote nothing — reflect reality
                a_startup.setChecked(startup.is_enabled())
        a_startup.toggled.connect(_toggle_startup)
        menu.addAction(a_startup)

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
