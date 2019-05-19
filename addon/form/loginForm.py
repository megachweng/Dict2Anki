# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'designer/loginForm.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(618, 581)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.webArea = QtWidgets.QGridLayout()
        self.webArea.setObjectName("webArea")
        self.gridLayout.addLayout(self.webArea, 1, 2, 1, 2)
        self.reloadBtn = QtWidgets.QPushButton(Form)
        self.reloadBtn.setObjectName("reloadBtn")
        self.gridLayout.addWidget(self.reloadBtn, 0, 3, 1, 1)
        self.urlLineEdit = QtWidgets.QLineEdit(Form)
        self.urlLineEdit.setEnabled(False)
        self.urlLineEdit.setObjectName("urlLineEdit")
        self.gridLayout.addWidget(self.urlLineEdit, 0, 2, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.reloadBtn.setText(_translate("Form", "reload"))


