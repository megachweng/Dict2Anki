from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDialog, QListWidgetItem
from .form import wordGroupForm
import logging

logger = logging.getLogger('Dict2Anki.wordGroupDialog')


class WordGroupDialog(QDialog, wordGroupForm.Ui_Dialog):
    group_selected = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

    def init_data(self, groups: list, previousChecked=None):
        # 添加分组
        logger.info(f'单词本分组: {groups}, 上次选择: {previousChecked}')
        for groupName, groupValue in groups:
            item = QListWidgetItem()
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setText(groupName)
            item.setData(Qt.UserRole, groupValue)
            item.setCheckState(Qt.Unchecked)
            self.wordGroupListWidget.addItem(item)
        # 恢复上次选择的分组
        if previousChecked:
            for groupName, _ in previousChecked:
                items = self.wordGroupListWidget.findItems(groupName, Qt.MatchExactly)
                for item in items:
                    item.setCheckState(Qt.Checked)

    @property
    def selectedGroup(self):
        selectedGroup = []
        for index in range(self.wordGroupListWidget.count()):
            if self.wordGroupListWidget.item(index).checkState() == Qt.Checked:
                selectedGroup.append(
                    (self.wordGroupListWidget.item(index).text(),
                     self.wordGroupListWidget.item(index).data(Qt.UserRole),)
                )
        return selectedGroup


