import pytest
from PyQt5.QtCore import Qt

from addon.addonWindow import Windows
from addon.constants import VERSION
import json
from PyQt5.QtWidgets import QApplication
import sys


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
    # monkeypatch.delattr("requests.sessions.Session.request")
    pass


@pytest.fixture(scope='function')
def window(qtbot):
    event_loop = QApplication(sys.argv)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.wait(500)
    yield w


@pytest.mark.skip
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


@pytest.mark.skip
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


@pytest.mark.skip
@pytest.mark.parametrize('index', [0, 1])
def test_dictionary_combobox_change(qtbot, index, mocker, fresh_config):
    fresh_config['credential'] = [{'username': '0', 'password': '0', 'cookie': '0'},
                                  {'username': '1', 'password': '1', 'cookie': '1'}]
    mocker.patch('addon.addonWindow.mw.addonManager.getConfig', return_value=fresh_config)
    app = QApplication(sys.argv)
    w = Windows()
    qtbot.addWidget(w)
    qtbot.wait(500)
    w.dictionaryComboBox.setCurrentIndex(index)
    assert w.dictionaryComboBox.currentText() in w.currentDictionaryLabel.text()
    # assert w.usernameLineEdit.text() == fresh_config['credential'][index]['username']
    # assert w.passwordLineEdit.text() == fresh_config['credential'][index]['password']
    assert w.cookieLineEdit.text() == fresh_config['credential'][index]['cookie']


@pytest.mark.skip
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


@pytest.mark.skip
@pytest.mark.parametrize('words', [
    ['a', 'b', 'c', 'd'],
    []
])
def test_newWordWidget(window, words):
    window.insertWordToListWidget(words)
    assert [window.newWordListWidget.item(row).text() for row in range(window.newWordListWidget.count())] == words
    assert all(
        window.newWordListWidget.item(row).data(Qt.UserRole) is None for row in range(window.newWordListWidget.count()))


@pytest.mark.skip
@pytest.mark.parametrize('local_words,remote_words,test_index', [
    ([], [], 0),
    ([], ['a', 'b'], 1),
    (['a'], ['a'], 2),
    (['a'], ['a', 'b'], 3),
    (['a', 'b'], ['c', 'd'], 4),
    (['a', 'b'], ['c', 'b'], 5),
])
def test_fetch_word_and_compare(monkeypatch, mocker, window, qtbot, local_words, remote_words, test_index):
    mocker.patch('addon.dictionary.eudict.Eudict.getWordsByPage', return_value=remote_words)
    mocker.patch('addon.dictionary.eudict.Eudict.getTotalPage', return_value=1)
    mocker.patch('addon.addonWindow.getWordsByDeck', return_value=local_words)
    mocked_tooltip = mocker.patch('addon.addonWindow.tooltip')
    from addon.dictionary.eudict import Eudict
    window.selectedDict = Eudict
    window.selectedDict.groups = [('group_1', 'group_1_id')]
    qtbot.waitUntil(window.workerThread.isRunning, timeout=5000)
    window.getRemoteWordList(['group_1'])
    qtbot.wait(1000)
    item_in_list_widget = [window.newWordListWidget.item(row) for row in range(window.newWordListWidget.count())]
    item_in_del_widget = [window.needDeleteWordListWidget.item(row) for row in
                          range(window.needDeleteWordListWidget.count())]
    words_in_list_widget = [i.text() for i in item_in_list_widget]
    words_in_del_widget = [i.text() for i in item_in_del_widget]

    assert all([item.data(Qt.UserRole) is None for item in item_in_list_widget])
    if test_index == 0:
        assert item_in_list_widget == []
        assert item_in_del_widget == []
        assert mocked_tooltip.called_with('无需同步')
    elif test_index == 1:
        assert sorted(words_in_list_widget) == sorted(remote_words)
        assert item_in_del_widget == []
    elif test_index == 2:
        assert item_in_list_widget == []
        assert item_in_del_widget == []
        assert mocked_tooltip.called_with('无需同步')
    elif test_index == 3:
        assert words_in_list_widget == ['b']
        assert item_in_del_widget == []
    elif test_index == 4:
        assert sorted(words_in_list_widget) == sorted(remote_words)
        assert sorted(words_in_del_widget) == sorted(local_words)
    elif test_index == 5:
        assert words_in_list_widget == ['c']
        assert words_in_del_widget == ['a']
