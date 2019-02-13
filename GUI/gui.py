import sys

import PyQt5.QtWidgets as widgets

from PyQt5.QtCore import *
from PyQt5.QtGui import *

from PyQt5.QtWidgets import QMainWindow, QTextEdit, QFileDialog, QApplication
from PyQt5 import uic
#from PyQt5.uic import *


class MyWindow(QMainWindow):

    def __init__(self):
        super(MyWindow, self).__init__()
        uic.loadUi('MTChallenge.ui', self)

    def showDialog(self):

        fname = QFileDialog.getOpenFileName(self, 'Open file', '/home')

        if fname[0]:
            f = open(fname[0], 'r')

            with f:
                data = f.read()
                self.textEdit.setText(data)

    def browse_file():
        widgets.QFileDialog.getOpenFileName(filter = 'HTML-Datei (*.htm *.html) ;; SDLXLIFF-Datei (*.sdlxliff)')





if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()
    w.browse_button.clicked.connect(MyWindow.browse_file)
    w.show()

    sys.exit(app.exec_())
