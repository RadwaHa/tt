import vtk

class ROIViewer:
    def __init__(self, interactor, vtk_base):
        self.interactor = interactor
        self.vtk_base = vtk_base

        # Create an image plane widget
        self.plane_widget = vtk.vtkImagePlaneWidget()
        self.plane_widget.SetInteractor(self.interactor)
        self.plane_widget.SetInputData(self.vtk_base.imageReader.GetOutput())
        self.plane_widget.SetPlaneOrientationToZAxes()
        self.plane_widget.SetSliceIndex(self.vtk_base.imageDimensions[2] // 2)
        self.plane_widget.PlaceWidget()
        self.plane_widget.On()

    def get_roi_bounds(self):
        # Get the ROI bounds from the plane widget
        poly_data = vtk.vtkPolyData()
        self.plane_widget.GetPolyData(poly_data)
        return poly_data.GetBounds()

    def set_roi_bounds(self, bounds):
        # This is not supported by vtkImagePlaneWidget
        pass

    def on(self):
        self.plane_widget.On()

    def off(self):
        self.plane_widget.Off()