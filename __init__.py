
try:
    from aqt import mw
    from .addon.addonWindow import Windows
    from PyQt5.QtWidgets import QAction


    def showWindow():
        w = Windows()
        w.exec()


    action = QAction("Dick2Anki...", mw)
    action.triggered.connect(showWindow)
    mw.form.menuTools.addAction(action)

except ImportError:
    from PyQt5.QtWidgets import QApplication
    from addon.addonWindow import Windows
    import sys

    app = QApplication(sys.argv)
    window = Windows()
    window.show()
    sys.exit(app.exec())
