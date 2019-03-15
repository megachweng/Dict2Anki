from copy import deepcopy
from unittest import mock

import pytest

from addon.addonWindow import Windows
from addon.constants import VERSION
import json
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import sys
import os



@pytest.fixture
def fresh_config():
    return json.loads('''{
      "deck": "",
      "selectedDict": 0,
      "selectedGroup": null,
      "selectedApi": 0,
      "credential": [
        {
          "username": "",
          "password": "",
          "cookie": ""
        },
        {
          "username": "",
          "password": "",
          "cookie": ""
        }
      ],
      "definition": true,
      "sentence": true,
      "image": true,
      "phrase": true,
      "AmEPhonetic": true,
      "BrEPhonetic": true,
      "BrEPron": false,
      "AmEPron": true,
      "noPron": false
    }''')


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    monkeypatch.delattr("requests.sessions.Session.request")


@pytest.fixture(scope='function')
def window(qtbot):
    event_loop = QApplication(sys.argv)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.wait(500)
    yield w


def test_start_up_with_fresh_config(qtbot, mocker, fresh_config):
    app = QApplication(sys.argv)
    mocked_getConfig = mocker.patch('addon.addonWindow.mw.addonManager.getConfig', return_value=fresh_config)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.wait(200)
    assert VERSION in w.windowTitle()
    assert w.workerThread.isRunning()
    mocked_getConfig.assert_called()
    assert w.usernameLineEdit.text() == w.passwordLineEdit.text() == w.cookieLineEdit.text() == ''
    assert w.tabWidget.currentIndex() == 1


def test_version_check(qtbot, mocker, monkeypatch):
    mocked_VersionCheckWorker_run = mocker.patch('addon.addonWindow.VersionCheckWorker.run')
    mocked_askUser = mocker.patch('addon.addonWindow.askUser')
    app = QApplication(sys.argv)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.waitUntil(w.updateCheckThead.isRunning)
    mocked_VersionCheckWorker_run.assert_called()
    w.updateCheckWork.haveNewVersion.emit('xxx', 'yyy')
    qtbot.wait(100)
    mocked_askUser.assert_called_with(f'有新版本:xxx是否更新？\n\nyyy')


@pytest.mark.parametrize('index', [0, 1])
def test_dictionary_combobox_change(qtbot, index, mocker, fresh_config):
    fresh_config['credential'] = [{'username': '0', 'password': '0', 'cookie': '0'}, {'username': '1', 'password': '1', 'cookie': '1'}]
    mocker.patch('addon.addonWindow.mw.addonManager.getConfig', return_value=fresh_config)
    app = QApplication(sys.argv)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.wait(500)
    w.dictionaryComboBox.setCurrentIndex(index)
    assert w.dictionaryComboBox.currentText() in w.currentDictionaryLabel.text()
    assert w.usernameLineEdit.text() == fresh_config['credential'][index]['username']
    assert w.passwordLineEdit.text() == fresh_config['credential'][index]['password']
    assert w.cookieLineEdit.text() == fresh_config['credential'][index]['cookie']


def test_get_deck_list(qtbot, fresh_config, mocker):
    fresh_config['deck'] = 'b'
    mocker.patch('addon.addonWindow.mw.addonManager.getConfig', return_value=fresh_config)
    mocker.patch('addon.addonWindow.getDeckList', return_value=['a', 'b', 'c'])
    app = QApplication(sys.argv)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.wait(200)
    assert [w.deckComboBox.itemText(row) for row in range(w.deckComboBox.count())] == ['a', 'b', 'c']
    assert w.deckComboBox.currentText() == 'b'


@pytest.mark.parametrize('words', [
    ['a', 'b', 'c', 'd'],
    []
])
def test_query_word(window, words):
    window.insertWordToListWidget(words)
    assert [window.newWordListWidget.item(row).text() for row in range(window.newWordListWidget.count())] == words
