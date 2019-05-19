from PyQt5.QtCore import QUrl, pyqtSlot, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from .form import loginForm
from PyQt5.QtWidgets import QDialog


class LoginDialog(QDialog, loginForm.Ui_Form):
    loginSucceed = pyqtSignal(dict)

    def __init__(self, callback: callable, parent=None, url=None):
        super().__init__(parent)
        self.setupUi(self)
        self.loginCheckCallback = callback
        self.url = url or 'https://github.com/megachweng/Dict2Anki'
        self.urlLineEdit.setText(url)
        self.webView = LoginWebEngineView(self)
        self.webView.loadFinished.connect(self.checkLoginState)
        self.reloadBtn.clicked.connect(self.refresh)
        # 每次刷新检查登录状态
        self.webView.urlChanged.connect(self.urlChanged)
        self.refresh()
        self.webArea.addWidget(self.webView)

    def refresh(self):
        self.webView.cookieStore.deleteAllCookies()
        self.webView.load(QUrl(self.url))

    @pyqtSlot(QUrl)
    def urlChanged(self, qurl):
        self.urlLineEdit.setText(qurl.toString())

    @property
    def cookie(self):
        return self.webView.cookie

    @pyqtSlot()
    def checkLoginState(self):
        def contentLoaded(content):
            if self.loginCheckCallback(cookie=self.cookie, content=content, first_login=True):
                self.close()
                self.loginSucceed.emit(self.cookie)

        self.webView.page().toHtml(contentLoaded)


class LoginWebEngineView(QWebEngineView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 绑定cookie被添加的信号槽
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setHttpUserAgent(
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko)'
            ' Chrome/69.0.3497.100 Safari/537.36'
        )
        self.cookieStore = self.profile.cookieStore()
        self.cookieStore.cookieAdded.connect(self.onCookieAdd)

        self._cookies = {}
        self.show()

    def onCookieAdd(self, cookie):
        name = cookie.name().data().decode('utf-8')
        value = cookie.value().data().decode('utf-8')
        self._cookies[name] = value

    @property
    def cookie(self) -> dict:
        return self._cookies
