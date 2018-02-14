# -*- coding: utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
# Anki
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser, tooltip

# Mywindow
from Dict2Anki.window import Window


def runPlugin():
    try:
        global __window
        __window = Window()
    except Exception, e:
        traceback.print_exc(file=open('error.log', 'w+'))


# create menu item
action = QAction("Import your WordBook", mw)
mw.connect(action, SIGNAL("triggered()"), runPlugin)
mw.form.menuTools.addAction(action)
