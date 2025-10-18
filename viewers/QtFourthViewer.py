from .FourthViewer import *
from .QtOrthoViewer import QtOrthoViewer
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import pyqtSignal

class QtFourthViewer(QtOrthoViewer):
    def __init__(self, parent=None, label="Fourth Viewer"):
        super().__init__(parent, label=label)
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Outline Mode", "Oblique Plane Mode"])
        self.mainLayout.addWidget(self.mode_selector)
        self.mode_selector.currentIndexChanged.connect(self.update_mode)

    def update_mode(self, index):
        outline_actor = self.get_outline_actor()
        if index == 0: # Outline Mode
            self.viewer.GetImageActor().SetVisibility(False)
            self.viewer.GetRenderer().AddActor(outline_actor)
            self.update_outline()
        elif index == 1: # Oblique Plane Mode
            self.viewer.GetImageActor().SetVisibility(True)
            self.viewer.GetRenderer().RemoveActor(outline_actor)

    def get_outline_actor(self):
        if not hasattr(self, "outline_actor"):
            self.outline_actor = vtk.vtkActor()
            self.outline_mapper = vtk.vtkPolyDataMapper()
            self.outline_actor.SetMapper(self.outline_mapper)
            self.outline_actor.GetProperty().SetColor(1, 0, 0)
        return self.outline_actor

    def update_oblique(self, caller, event):
        if self.mode_selector.currentIndex() == 1:
            self.viewer.Render()