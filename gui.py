import sys
import os.path
import textwrap
from distutils import util

from PyQt5 import QtCore, uic
from PyQt5.QtWidgets import qApp, QApplication, QFileDialog, QMainWindow, QMessageBox
from PyQt5.QtGui import QIcon

import pandas as pd
import numpy as np

from matplotlib.backends.qt_compat import QtWidgets
from matplotlib.backends.backend_qt5agg import (FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure

from source.parsing import read_from_file
from source.utils import new_translation, match_target_mt, save_cache, range_positive
from source.sampling import new_sample
from source.calculation import pe_density
from source.settings import SettingsWindow


class MyWindow(QMainWindow):

    def __init__(self):
        super(MyWindow, self).__init__()
        self.init_ui()
        # Load settings
        self.settings = QtCore.QSettings("Lev Corp.", "woerdle-zehla")

    def init_ui(self):
        uic.loadUi(os.path.join('GUI', 'MTChallenge.ui'), self)
        self.setWindowTitle('Wördlezehla')
        self.setWindowIcon(QIcon(os.path.join('GUI', 'Icon.png')))
        self.setContentsMargins(7, 0, 7, 0)
        self.statusBar().showMessage('Ready')

        self.show()

    @staticmethod
    def browse_file():
        """Open file dialog and write name to line edit"""
        text = QFileDialog.getOpenFileName(filter='HTML-Datei (*.htm *.html) ;; SDLXLIFF-Datei (*.sdlxliff)')[0]
        w.input_file_line_edit.setText(text)

    def open_settings(self):
        w.s_dialog = SettingsWindow(w)

    @staticmethod
    def plot_results():
        app = ApplicationWindow()
        app.show()

    def run_sample(self):
        """Sample segments from input file and write alpha_share to text edit"""
        w.df, w.cache = read_from_file(w.input_file_line_edit.text())
        sample_size = w.sample_size_box.value()
        w.sample_object, alpha_share = new_sample(w.df, sample_size=sample_size)
        w.textOutput.setText(str("The sample's share of translatable characters is {:.1f}%".format(alpha_share * 100)))

    def run_calculation(self):
        """Calculate post-edit density results and create separate outputs.

        By enabling/ignoring version information, you tell the function to either:
            a) create a new dataframe from the input file
            b) populate the dataframe with translations called via the MT provider API
        The function then calculates post-edit density scores from the dataframe and stores the data in the cache.
        Cache information is then passed to different outputs:
            - the Output line edit
            - Optional: A json file saved manually or via the autosave function set in settings.
        """
        
        if w.ignore_history_false.isChecked():
            w.df, w.cache = read_from_file(w.input_file_line_edit.text(), versions=True)

        else:
            w.df = new_translation(w.df, w.cache, w.sample_object)

        source_list, target_list, mt_list = match_target_mt(w.df)

        w.cache = pe_density(source_list, target_list, mt_list, w.cache)
        w.actionSave_as.setEnabled(True)
        w.textOutput.setText(str('Your Post-Edit Density score is {:.3f}\n'.format(w.cache['ped'])))
        w.statistics()

        w.autosave()

    def autosave(self):
        if util.strtobool(w.settings.value("autosave", "")):
            w.save_as(auto=True)

    def print_details(self, apples_or_peaches):
        """Helper function for printing PED details"""
        wrapper = textwrap.TextWrapper(subsequent_indent=' '*20)
        count = 0
        for value in apples_or_peaches.values():

            w.textOutput.append('PED = {:.3f}'.format(value[0]))
            w.textOutput.append('MT Output  : ' + str(wrapper.fill(text=value[2])))
            w.textOutput.append('Target Übs : ' + str(wrapper.fill(text=value[3])) + '\n')

            count += 1
            if count == 10:
                break

    def save_as(self, auto=False):

        file_format = 'ped{:.3f}_{}___{}.json'.format(w.cache['ped'], w.cache['Relation'], w.cache['Project'])

        if auto:
            fp = os.path.join(w.settings.value("autosave_folder", ""), file_format)
        else:
            fp = QFileDialog.getSaveFileName(filter='JSON-Datei (*.json)', directory=file_format)[0]

        try:
            save_cache(fp, w.cache)

        except OSError:
            QMessageBox.warning(w, "Warning", "Not a valid path for saving!")

    def statistics(self, ba_limit=0.4, pp_limit=0.05):
        """Run additional statistics on Levenshtein distance results

        Arguments:
            cache -- containing a dictionary with Levenshtein results on a string level
            ba_limit -- as lower limit for the bad_apples classification
            pp_limit -- as upper limit for the peach perfect classification

        Prints detailed results for review purposes
            bad_apples -- dictionary for benchmarking strings with high pe efforts (Bad Apples)
            peach_perfect -- dictionary for benchmarking strings with minimal pe efforts (Peach Perfects)

        Returns:
            None
        """
        # TODO: Add BA and PP limits to app settings
        bad_apples = {k: v for k, v in w.cache['ped_details'].items() if v[0] >= ba_limit}
        peach_perfect = {k: v for k, v in w.cache['ped_details'].items() if v[0] <= pp_limit}

        if len(bad_apples) > 0:
            w.textOutput.append(str('---Zu den Bad Apples (PED >= {}) gehören folgende Strings---\n'.format(ba_limit)))
            w.print_details(bad_apples)

        else:
            w.textOutput.append(str('---Super! Es gibt keine Bad Apples (PED <= {})\n'.format(ba_limit)))

        if len(peach_perfect) > 0:
            w.textOutput.append(str('---Zu den Peach Perfects (PED <= {}) gehören folgende Strings---\n'.
                                    format(pp_limit)))
            w.print_details(peach_perfect)

        else:
            w.textOutput.append(str('---Es gibt leider keine Peach Perfects (PED <= {})\n'.format(pp_limit)))


class ApplicationWindow(QtWidgets.QMainWindow):
    """Show results in new window

    Source: https://matplotlib.org/gallery/user_interfaces/embedding_in_qt_sgskip.html
    """
    def __init__(self):
        super().__init__()
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        layout = QtWidgets.QVBoxLayout(self._main)

        static_canvas = FigureCanvas(Figure(figsize=(5, 4)))
        layout.addWidget(static_canvas)
        self.addToolBar(NavigationToolbar(static_canvas, self))

        self._static_ax = static_canvas.figure.subplots()
        df = pd.DataFrame.from_dict(data={k: v[0] for k, v in w.cache['ped_details'].items()},
                                    orient='index', columns=['ped'])

        #bin_edges = [x for x in range_positive(0, df['ped'].max() + 0.05, 0.05)]
        # Uncomment to use the numpy implementation instead
        bin_edges = np.arange(0, df['ped'].max()+0.05, 0.05)
        xlabel = str('Post-edit density (Agg. score: {:.3f})'.format(w.cache['ped']))
        ylabel = str('Number of segments ({} seg. total)'.format(len(w.cache['ped_details'])))

        self._static_ax.hist(data=df, x=df['ped'], bins=bin_edges)
        self._static_ax.set_xlabel(xlabel)
        self._static_ax.set_ylabel(ylabel)


if __name__ == '__main__':

    app = QApplication(sys.argv)
    w = MyWindow()
    w.plot_button.clicked.connect(MyWindow.plot_results)
    w.calculate_button.clicked.connect(MyWindow.run_calculation)
    w.sample_button.clicked.connect(MyWindow.run_sample)
    w.browse_button.clicked.connect(MyWindow.browse_file)
    w.actionOpen_File.triggered.connect(MyWindow.browse_file)
    w.actionExit.triggered.connect(qApp.quit)
    w.actionSave_as.triggered.connect(MyWindow.save_as)
    w.actionSettings.triggered.connect(MyWindow.open_settings)

    sys.exit(app.exec_())
