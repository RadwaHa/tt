from .OrthoViewer import *
from skimage import measure
from vtk.util import numpy_support

class FourthViewer(OrthoViewer):
    def __init__(self, vtkBaseClass, orientation, label: str = "Fourth Viewer"):
        super().__init__(vtkBaseClass, orientation, label)

        # The Fourth Viewer should not have a reslice cursor widget
        if self.resliceCursorWidget:
            self.resliceCursorWidget.Off()
            self.resliceCursorWidget = None

        self.outline_actor = None
        self.reslice_actor = vtk.vtkImageActor()
        self.reslice_axes = vtk.vtkMatrix4x4()

    def show_outline(self, slice_index):
        if self.outline_actor:
            self.renderer.RemoveActor(self.outline_actor)
            self.outline_actor = None

        image_data = self.vtkBaseClass.imageReader.GetOutput()
        if not image_data or image_data.GetDimensions() == (0, 0, 0) or slice_index is None:
            self.render()
            return

        # Step 1: Threshold the image to create a binary mask of potential structures.
        thresholder = vtk.vtkImageThreshold()
        thresholder.SetInputData(image_data)
        thresholder.ThresholdByLower(150)  # A reasonable starting point for soft tissue
        thresholder.SetInValue(1)
        thresholder.SetOutValue(0)
        thresholder.Update()

        # Step 2: Use ImageConnectivityFilter to find the largest connected region (the organ).
        connectivity_filter = vtk.vtkImageConnectivityFilter()
        connectivity_filter.SetInputConnection(thresholder.GetOutputPort())
        connectivity_filter.SetExtractionModeToLargestRegion()
        connectivity_filter.Update()
        mask_data = connectivity_filter.GetOutput()

        # Step 3: Convert the resulting mask volume to a NumPy array.
        dims = mask_data.GetDimensions()
        scalars = mask_data.GetPointData().GetScalars()
        if not scalars:
            self.render()
            return
        np_array = numpy_support.vtk_to_numpy(scalars).reshape(dims[2], dims[1], dims[0])

        # Ensure slice_index is within bounds
        if slice_index >= np_array.shape[0]:
            slice_index = np_array.shape[0] - 1

        current_slice = np_array[slice_index, :, :]

        # Step 4: Find contours on the 2D slice of the largest region.
        contours = measure.find_contours(current_slice, 0.5)

        # Create a polydata object to store the contours
        poly_data = vtk.vtkPolyData()
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()

        point_id_offset = 0
        for contour in contours:
            line = vtk.vtkPolyLine()
            line.GetPointIds().SetNumberOfIds(len(contour))
            for i, point in enumerate(contour):
                point_id = points.InsertNextPoint(point[1], point[0], 0)
                line.GetPointIds().SetId(i, point_id)
            lines.InsertNextCell(line)

        poly_data.SetPoints(points)
        poly_data.SetLines(lines)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)

        self.outline_actor = vtk.vtkActor()
        self.outline_actor.SetMapper(mapper)
        self.outline_actor.GetProperty().SetColor(1, 0, 0)
        self.renderer.AddActor(self.outline_actor)
        self.render()

    def show_oblique_plane(self):
        image_data = self.vtk_base_class.imageReader.GetOutput()
        if not image_data or image_data.GetDimensions() == (0, 0, 0):
            return

        # Hide the orthogonal slice actor
        self.slice_actor.VisibilityOff()

        # Get the reslice axes from the base class
        self.reslice_axes = self.vtk_base_class.get_reslice_axes()

        # Create the image reslice
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(image_data)
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxes(self.reslice_axes)
        reslice.SetInterpolationModeToLinear()

        # Create a lookup table to map the image values to colors
        table = vtk.vtkLookupTable()
        table.SetRange(0, 1000) # image intensity range
        table.SetValueRange(0.0, 1.0) # from black to white
        table.SetSaturationRange(0.0, 0.0) # no color saturation
        table.SetRampToLinear()
        table.Build()

        # Map the image through the lookup table
        color = vtk.vtkImageMapToColors()
        color.SetLookupTable(table)
        color.SetInputConnection(reslice.GetOutputPort())

        self.reslice_actor.GetMapper().SetInputConnection(color.GetOutputPort())

        # Add the reslice actor to the renderer
        if self.reslice_actor not in self.renderer.GetActors():
            self.renderer.AddActor(self.reslice_actor)
        self.render()

    def show_orthogonal_slice(self):
        # Hide the reslice actor
        if self.reslice_actor in self.renderer.GetActors():
            self.reslice_actor.VisibilityOff()

        # Show the orthogonal slice actor
        self.slice_actor.VisibilityOn()
        self.render()