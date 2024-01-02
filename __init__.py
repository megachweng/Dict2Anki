try:
    from aqt import mw
    from .addon.addonWindow import Windows
    # from PyQt5.QtWidgets import QAction
    from aqt.qt import *


    def showWindow():
        w = Windows()
        w.exec()

    action = QAction("Dict2Anki...", mw)
    action.triggered.connect(showWindow)
    mw.form.menuTools.addAction(action)

except ImportError as err:
    import os
    # from PyQt5.QtWidgets import QApplication
    from aqt.qt import *
    from addon.addonWindow import Windows
    import sys
    if os.environ.get('DEVDICT2ANKI'):
        app = QApplication(sys.argv)
        window = Windows()
        window.show()
        sys.exit(app.exec())

    traceback.print_exc()
