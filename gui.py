import sys

import pandas as pd
from PyQt5 import uic
from PyQt5.QtWidgets import qApp, QApplication, QFileDialog, QMainWindow, QWidget

from PyQt5.QtGui import QIcon
import os.path
import random # required only for dummy plot

from matplotlib.backends.qt_compat import QtCore, QtWidgets, is_pyqt5
from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

import numpy as np
#from tutorial2 import ApplicationWindow
#matplotlib.use('Qt5Agg')
from scripts.parsing import read_from_file
from scripts.utils import new_sample, new_translation, query_yes_no, comp_entry
from scripts.calculation import new_calculation


class MyWindow(QMainWindow):

    def __init__(self):
        super(MyWindow, self).__init__()
        self.initUI()


    def initUI(self):

        uic.loadUi(os.path.join('GUI', 'MTChallenge.ui'), self)
        self.setWindowTitle('Wördlezehla')
        self.setWindowIcon(QIcon(os.path.join('GUI', 'Icon.png')))
        #self.QLayout.setContentsMargins(11,11,11,11)
        self.statusBar().showMessage('Ready')

        self.show()


    def browse_file():
        text = QFileDialog.getOpenFileName(filter = 'HTML-Datei (*.htm *.html) ;; SDLXLIFF-Datei (*.sdlxliff)')[0]
        w.input_file_line_edit.setText(text)

    def plot_results():
        app = ApplicationWindow()
        app.show()

    def run_sample():
        '''Dummy function for sampling'''
        w.df, w.cache = read_from_file(w.input_file_line_edit.text())
        w.sample_object, w.source, alpha_share = new_sample(w.df, sample_size=50)
        w.textOutput.setText(str("The sample's share of translatable characters is {:.1f}%".format(alpha_share * 100)))

    def run_calculation():
        '''Dummy function for API call and calculations'''
        target_list, mt_list, w.cache = new_translation(w.df, w.cache, w.sample_object, w.source)
        w.cache = new_calculation(target_list, mt_list, w.cache)
        w.textOutput.setText(str('Your Post-Edit Density score is {:.3f}\n'.format(w.cache['ped'])))

    def submit_entry():
        '''Dummy function for submitting entries'''
        my_list2 = [6, 7, 8]
        w.textOutput.setText(str(my_list2))

class ApplicationWindow(QtWidgets.QMainWindow):
    '''Show results in new window
    Source: https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html
    '''
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        static_canvas = FigureCanvas(Figure(figsize=(5, 3)))
        layout.addWidget(static_canvas)
        self.addToolBar(NavigationToolbar(static_canvas, self))


        self._static_ax = static_canvas.figure.subplots()
        #t = np.linspace(0, 10, 501)
        #self._static_ax.plot(t, np.tan(t), ".")


if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()
    w.plot_button.clicked.connect(MyWindow.plot_results)
    w.submit_button.clicked.connect(MyWindow.submit_entry)
    w.calculate_button.clicked.connect(MyWindow.run_calculation)
    w.sample_button.clicked.connect(MyWindow.run_sample)
    w.browse_button.clicked.connect(MyWindow.browse_file)
    w.actionOpen_File.triggered.connect(MyWindow.browse_file)
    w.actionExit.triggered.connect(qApp.quit)


    sys.exit(app.exec_())
