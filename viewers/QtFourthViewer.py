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
        self.mode_selector.addItems(["Normal", "Outline Mode", "Oblique Plane Mode"])
        self.mainLayout.addWidget(self.mode_selector)

    def connect(self):
        super().connect()
        self.mode_selector.currentIndexChanged.connect(self.update_mode)
        self.slider.valueChanged.connect(self.slice_changed.emit)

    def update_mode(self, index):
        if index == 0: # Normal
            pass
        elif index == 1: # Outline Mode
            pass
        elif index == 2: # Oblique Plane Mode
            pass

    def set_detection_results(self, results):
        self.detection_results = results
        if self.mode_selector.currentIndex() == 1:
            self.update_slice_outline(self.viewer.get_slice())

    def update_slice_outline(self, slice_index):
        if self.mode_selector.currentIndex() == 1:
            if self.detection_results and slice_index < len(self.detection_results):
                self.viewer.show_outline(self.detection_results[slice_index])
            else:
                self.viewer.show_outline(None)