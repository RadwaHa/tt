from .FourthViewer import *
from .QtOrthoViewer import QtOrthoViewer
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import pyqtSignal

class QtFourthViewer(QtOrthoViewer):
    slice_changed = pyqtSignal(int)

    def __init__(self, vtkBaseClass, orientation, label: str = "Fourth Viewer"):
        super().__init__(vtkBaseClass, orientation, label)
        self.viewer = FourthViewer(vtkBaseClass, orientation, label)
        self.detection_results = None
        self._init_UI()
        self.connect()

    def _init_UI(self):
        super()._init_UI()
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Outline Mode", "Oblique Plane Mode"])
        self.mainLayout.addWidget(self.mode_selector)

    def connect(self):
        super().connect()
        self.mode_selector.currentIndexChanged.connect(self.update_mode)
        self.slider.valueChanged.connect(self.slice_changed.emit)

    def update_mode(self, index):
        if index == 0: # Outline Mode
            self.viewer.slice_actor.VisibilityOff()
            self.update_slice_outline(self.viewer.get_slice())
        elif index == 1: # Oblique Plane Mode
            self.viewer.show_oblique_plane()

    def set_detection_results(self, results):
        self.detection_results = results
        if self.mode_selector.currentIndex() == 0:
            self.update_slice_outline(self.viewer.get_slice())

    def update_slice_outline(self, slice_index):
        if self.mode_selector.currentIndex() == 0:
            self.viewer.show_outline(slice_index)
        else:
            self.viewer.show_outline(None)

    def update_oblique(self):
        if self.mode_selector.currentIndex() == 1:
            self.viewer.show_oblique_plane()