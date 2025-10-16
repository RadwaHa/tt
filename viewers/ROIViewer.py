import vtk

class ROIViewer:
    def __init__(self, interactor, vtk_base):
        self.interactor = interactor
        self.vtk_base = vtk_base
        self.box_widget = vtk.vtkBoxWidget()
        self.box_widget.SetInteractor(self.interactor)
        self.box_widget.SetPlaceFactor(1.0)
        self.box_widget.SetInputData(self.vtk_base.imageReader.GetOutput())
        self.box_widget.PlaceWidget()
        self.box_widget.On()

    def get_roi_bounds(self):
        bounds = self.box_widget.GetPlacedBounds()
        return bounds

    def set_roi_bounds(self, bounds):
        self.box_widget.PlaceWidget(bounds)

    def on(self):
        self.box_widget.On()

    def off(self):
        self.box_widget.Off()