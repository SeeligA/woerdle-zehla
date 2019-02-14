import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QWidget
from PyQt5.QtGui import QIcon


class MyWindow(QMainWindow):

    def __init__(self):
        super(MyWindow, self).__init__()
        self.initUI()


    def initUI(self):
        uic.loadUi('MTChallenge.ui', self)
        self.setWindowTitle('Wördlezehla')

        self.show()

    def browse_file(self):
        text = QFileDialog.getOpenFileName(filter = 'HTML-Datei (*.htm *.html) ;; SDLXLIFF-Datei (*.sdlxliff)')[0]
        w.input_file_line_edit.setText(text)




if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()

    w.browse_button.clicked.connect(MyWindow.browse_file)



    sys.exit(app.exec_())
