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

    def browse_file(self):
        text = widgets.QFileDialog.getOpenFileName(filter = 'HTML-Datei (*.htm *.html) ;; SDLXLIFF-Datei (*.sdlxliff)')[0]
        w.input_file_line_edit.setText(text)




if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()
    w.setWindowTitle('Wördlezehla')
    w.browse_button.clicked.connect(MyWindow.browse_file)

    w.show()

    sys.exit(app.exec_())