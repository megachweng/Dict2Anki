# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'designer/loginDialog.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

# from PyQt5 import QtCore, QtGui, QtWidgets
# from aqt import QtCore, QtGui, QtWidgets
import aqt

class Ui_LoginDialog(object):
    def setupUi(self, LoginDialog):
        LoginDialog.setObjectName("LoginDialog")
        LoginDialog.resize(505, 480)
        self.gridLayout = aqt.QGridLayout(LoginDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.reloadBtn = aqt.QPushButton(LoginDialog)
        self.reloadBtn.setObjectName("reloadBtn")
        self.gridLayout.addWidget(self.reloadBtn, 0, 1, 1, 1)
        self.pageContainer = aqt.QVBoxLayout()
        self.pageContainer.setObjectName("pageContainer")
        self.gridLayout.addLayout(self.pageContainer, 1, 0, 1, 2)
        self.address = aqt.QLineEdit(LoginDialog)
        self.address.setClearButtonEnabled(True)
        self.address.setObjectName("address")
        self.gridLayout.addWidget(self.address, 0, 0, 1, 1)

        self.retranslateUi(LoginDialog)
        aqt.QMetaObject.connectSlotsByName(LoginDialog)

    def retranslateUi(self, LoginDialog):
        _translate = aqt.QCoreApplication.translate
        LoginDialog.setWindowTitle(_translate("LoginDialog", "Login"))
        self.reloadBtn.setText(_translate("LoginDialog", "reload"))


