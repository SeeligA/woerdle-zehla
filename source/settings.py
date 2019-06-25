from distutils import util

from PyQt5 import uic, QtWidgets, QtCore
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QIcon
import os


class SettingsWindow(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.initUI()
        self.settings = QtCore.QSettings("Lev Corp.", "woerdle-zehla")

        autosave = util.strtobool(self.settings.value("autosave", ""))
        self.auto_save_checkbox.setChecked(autosave)

        save_folder = self.settings.value("autosave_folder", "")
        self.auto_save_line.setText(save_folder)

    def initUI(self):
        uic.loadUi(os.path.join('GUI', 'settings.ui'), self)
        self.setWindowTitle('Wördlezehla')
        self.setWindowIcon(QIcon(os.path.join('GUI', 'Icon.png')))
        self.setContentsMargins(7, 0, 7, 0)

        self.auto_save_checkbox.clicked.connect(self.set_autosave)
        self.auto_save_browse_button.clicked.connect(self.set_folder)

        self.show()

    def set_autosave(self):
        self.settings.setValue("autosave", self.auto_save_checkbox.isChecked())

    def set_folder(self):
        """Open file dialog and write dirpath to line edit."""
        save_folder = QFileDialog.getExistingDirectory()
        self.auto_save_line.setText(save_folder)
        self.settings.setValue("autosave_folder", save_folder)
