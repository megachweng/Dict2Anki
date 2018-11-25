from PyQt5.QtCore import QObject, pyqtSignal


class DictSignals(QObject):
    loginSucceed = pyqtSignal()
    loginFailed = pyqtSignal()
    exceptionOccurred = pyqtSignal(object)
    setTotalTasks = pyqtSignal(int)
    updateProgress = pyqtSignal()
    log = pyqtSignal(str)


class APISignals(QObject):
    exceptionOccurred = pyqtSignal(object)
    setTotalTasks = pyqtSignal(int)
    updateProgress = pyqtSignal()
    log = pyqtSignal(str)


