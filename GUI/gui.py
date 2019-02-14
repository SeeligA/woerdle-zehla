import sys


from PyQt5 import uic
from PyQt5.QtWidgets import qApp, QApplication, QFileDialog, QMainWindow, QWidget
from PyQt5.QtGui import QIcon

import random # required only for dummy plot

from matplotlib.backends.backend_qt5agg import FigureCanvasAgg as Canvas
from matplotlib.figure import Figure # required only for dummy plot
import numpy as np
#matplotlib.use('Qt5Agg')



class MyWindow(QMainWindow):

    def __init__(self):
        super(MyWindow, self).__init__()
        self.initUI()


    def initUI(self):

        uic.loadUi('MTChallenge.ui', self)
        self.setWindowTitle('Wördlezehla')
        self.setWindowIcon(QIcon('Icon.png'))
        #self.QLayout.setContentsMargins(11,11,11,11)
        self.statusBar().showMessage('Ready')

        self.show()


    def browse_file():
        text = QFileDialog.getOpenFileName(filter = 'HTML-Datei (*.htm *.html) ;; SDLXLIFF-Datei (*.sdlxliff)')[0]
        w.input_file_line_edit.setText(text)


    def run_sample():
        '''Dummy function for sampling'''
        my_list = [1, 2, 3]
        w.textOutput.setText(str(my_list))

    def run_calculation():
        '''Dummy function for API call and calculations'''
        my_list2 = [3, 4, 5]
        w.textOutput.setText(str(my_list2))

    def submit_entry():
        '''Dummy function for submitting entries'''
        my_list2 = [6, 7, 8]
        w.textOutput.setText(str(my_list2))




if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()
    #w.plot_button.clicked.connect(MyWindow.plot_sample)
    w.submit_button.clicked.connect(MyWindow.submit_entry)
    w.calculate_button.clicked.connect(MyWindow.run_calculation)
    w.sample_button.clicked.connect(MyWindow.run_sample)
    w.browse_button.clicked.connect(MyWindow.browse_file)
    w.actionOpen_File.triggered.connect(MyWindow.browse_file)
    w.actionExit.triggered.connect(qApp.quit)


    sys.exit(app.exec_())
