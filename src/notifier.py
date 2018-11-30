from PyQt5.QtCore import pyqtSignal, QThread
import requests
from distutils.version import StrictVersion


class Version(QThread):
    hasNewVersion = pyqtSignal(object)
    log = pyqtSignal(str)
    url = 'https://api.github.com/repos/megachweng/Dict2Anki/releases/latest'

    def __init__(self, currentVersion):
        super().__init__()
        self.currentVersion = StrictVersion(currentVersion)

    def run(self):
        try:
            self.log.emit('检查新版本')
            rsp = requests.get(self.url, timeout=10)
            version = rsp.json()['name'][1:]
            if StrictVersion(version) > self.currentVersion:
                self.hasNewVersion.emit(version)
            else:
                self.log.emit(f'当前为最新版本:{self.currentVersion}')
        except Exception as e:
            self.log.emit(f'版本检查失败{e}')
