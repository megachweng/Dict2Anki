from PyQt5.QtCore import pyqtSignal, QObject


class DictSIG(QObject):
    saveCookie = pyqtSignal(object)
    exceptionOccurred = pyqtSignal(object)
    wordsReady = pyqtSignal(object)
    progress = pyqtSignal()
    totalTasks = pyqtSignal(int)
    log = pyqtSignal(str)


class APISIG(QObject):
    exceptionOccurred = pyqtSignal(object)
    wordsReady = pyqtSignal(object)
    progress = pyqtSignal()
    totalTasks = pyqtSignal(int)
    log = pyqtSignal(str)


class AudioDownloaderSIG(QObject):
    exceptionOccurred = pyqtSignal(object)
    downloadFinished = pyqtSignal()
    progress = pyqtSignal()
    totalTasks = pyqtSignal(int)
    log = pyqtSignal(str)
