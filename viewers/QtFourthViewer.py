from PyQt5.QtWidgets import QComboBox, QLabel, QVBoxLayout
from PyQt5.QtCore import pyqtSignal
from .QtOrthoViewer import QtOrthoViewer
import vtk
from vtk.util import numpy_support
import numpy as np
from skimage import measure, morphology


class QtFourthViewer(QtOrthoViewer):
    """
    Fourth viewer with two modes:
    1. Outline Mode: Shows contours of organs in selected slice
    2. Oblique Mode: Shows oblique plane perpendicular to rotated reference line
    """
    
    def __init__(self, parent=None, label="Fourth Viewer"):
        super().__init__(parent, orientation=0, label=label)
        
        # Properties for fourth viewer
        self.current_mode = "outline"  # "outline" or "oblique"
        self.source_orientation = 0  # Which viewer to get outline from (0=axial, 1=coronal, 2=sagittal)
        self.source_slice_index = 0
        
        # VTK actors for display
        self.outline_actor = None
        self.oblique_image_actor = vtk.vtkImageActor()
        
        # Oblique plane properties
        self.oblique_angle = 0  # Rotation angle in degrees
        self.oblique_center = [0, 0, 0]  # Center point for oblique plane
        
        # Add mode selector UI
        self._setup_mode_selector()
        
        # Hide the default reslice cursor widget
        if self.viewer.resliceCursorWidget:
            self.viewer.resliceCursorWidget.Off()
    
    def _setup_mode_selector(self):
        """Add UI controls for mode selection"""
        # Mode selector
        self.mode_label = QLabel("Display Mode:")
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Outline Mode", "Oblique Plane Mode"])
        self.mode_selector.currentIndexChanged.connect(self.on_mode_changed)
        
        # Source view selector (for outline mode)
        self.source_label = QLabel("Source View:")
        self.source_selector = QComboBox()
        self.source_selector.addItems(["Axial", "Coronal", "Sagittal"])
        self.source_selector.currentIndexChanged.connect(self.on_source_changed)
        
        # Add to layout
        controls_layout = QVBoxLayout()
        controls_layout.addWidget(self.mode_label)
        controls_layout.addWidget(self.mode_selector)
        controls_layout.addWidget(self.source_label)
        controls_layout.addWidget(self.source_selector)
        self.mainLayout.addLayout(controls_layout)
    
    def on_mode_changed(self, index):
        """Handle mode change"""
        self.current_mode = "outline" if index == 0 else "oblique"
        
        # Show/hide appropriate controls
        self.source_label.setVisible(self.current_mode == "outline")
        self.source_selector.setVisible(self.current_mode == "outline")
        
        # Update display
        self.update_display()
    
    def on_source_changed(self, index):
        """Handle source view change for outline mode"""
        self.source_orientation = index
        if self.current_mode == "outline":
            self.update_display()
    
    def update_slice_outline(self, slice_index):
        """Called when slice changes in one of the orthogonal viewers"""
        self.source_slice_index = slice_index
        if self.current_mode == "outline":
            self.show_outline()
    
    def update_oblique(self, caller=None, event=None):
        """Called when oblique plane parameters change"""
        if self.current_mode == "oblique":
            self.show_oblique_plane()
    
    def update_display(self):
        """Update display based on current mode"""
        if self.current_mode == "outline":
            self.show_outline()
        else:
            self.show_oblique_plane()
    
    def show_outline(self):
        """
        Extract and display contours from the selected slice.
        This creates an outline view of organs in the current slice.
        """
        # Remove previous outline actor
        if self.outline_actor:
            self.viewer.GetRenderer().RemoveActor(self.outline_actor)
            self.outline_actor = None
        
        # Hide oblique actor
        self.oblique_image_actor.SetVisibility(False)
        
        # Get image data
        image_data = self.viewer.vtkBaseClass.imageReader.GetOutput()
        if not image_data or image_data.GetDimensions() == (0, 0, 0):
            self.viewer.Render()
            return
        
        # Convert VTK image to numpy array
        dims = image_data.GetDimensions()
        scalars = image_data.GetPointData().GetScalars()
        if not scalars:
            self.viewer.Render()
            return
        
        np_array = numpy_support.vtk_to_numpy(scalars)
        np_array = np_array.reshape(dims[2], dims[1], dims[0])  # Z, Y, X
        
        # Get the appropriate slice based on source orientation
        if self.source_orientation == 0:  # Axial (XY plane)
            if self.source_slice_index >= np_array.shape[0]:
                self.source_slice_index = np_array.shape[0] - 1
            current_slice = np_array[self.source_slice_index, :, :]
        elif self.source_orientation == 1:  # Coronal (XZ plane)
            if self.source_slice_index >= np_array.shape[1]:
                self.source_slice_index = np_array.shape[1] - 1
            current_slice = np_array[:, self.source_slice_index, :]
        else:  # Sagittal (YZ plane)
            if self.source_slice_index >= np_array.shape[2]:
                self.source_slice_index = np_array.shape[2] - 1
            current_slice = np_array[:, :, self.source_slice_index]
        
        # Process the slice to extract contours
        contours = self._extract_contours(current_slice)
        
        if not contours:
            self.viewer.Render()
            return
        
        # Create VTK polydata for contours
        poly_data = vtk.vtkPolyData()
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()
        
        for contour in contours:
            # Create a polyline for this contour
            polyline = vtk.vtkPolyLine()
            num_points = len(contour)
            polyline.GetPointIds().SetNumberOfIds(num_points)
            
            for i, point in enumerate(contour):
                # Add point (swap Y coordinate for proper orientation)
                point_id = points.InsertNextPoint(point[1], point[0], 0)
                polyline.GetPointIds().SetId(i, point_id)
            
            lines.InsertNextCell(polyline)
        
        poly_data.SetPoints(points)
        poly_data.SetLines(lines)
        
        # Create mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly_data)
        
        self.outline_actor = vtk.vtkActor()
        self.outline_actor.SetMapper(mapper)
        self.outline_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # Red
        self.outline_actor.GetProperty().SetLineWidth(2)
        
        # Add to renderer
        self.viewer.GetRenderer().AddActor(self.outline_actor)
        self.viewer.GetRenderer().ResetCamera()
        self.viewer.Render()
    
    def _extract_contours(self, slice_array):
        """
        Extract contours from a 2D slice using image processing.
        Returns list of contour point arrays.
        """
        # Normalize to 0-1 range
        slice_min = slice_array.min()
        slice_max = slice_array.max()
        if slice_max > slice_min:
            normalized = (slice_array - slice_min) / (slice_max - slice_min)
        else:
            return []
        
        # Apply threshold to create binary mask
        # Use Otsu's method for automatic thresholding
        try:
            from skimage.filters import threshold_otsu
            threshold = threshold_otsu(normalized)
        except:
            threshold = 0.3  # Fallback threshold
        
        binary_mask = normalized > threshold
        
        # Clean up the mask
        binary_mask = morphology.remove_small_objects(binary_mask, min_size=100)
        binary_mask = morphology.binary_closing(binary_mask, morphology.disk(3))
        
        # Find contours
        contours = measure.find_contours(binary_mask, 0.5)
        
        # Filter out very small contours
        contours = [c for c in contours if len(c) > 20]
        
        return contours
    
    def show_oblique_plane(self):
        """
        Display an oblique plane that is perpendicular to the rotated reference line.
        The plane rotates around the center point based on the reference line angle.
        """
        # Hide outline actor
        if self.outline_actor:
            self.viewer.GetRenderer().RemoveActor(self.outline_actor)
        
        # Get image data
        image_data = self.viewer.vtkBaseClass.imageReader.GetOutput()
        if not image_data or image_data.GetDimensions() == (0, 0, 0):
            return
        
        # Get oblique parameters from reslice cursor
        # The reslice cursor maintains the center point and orientation
        reslice_cursor = self.viewer.vtkBaseClass.resliceCursor
        self.oblique_center = reslice_cursor.GetCenter()
        
        # Get the reslice axes (defines the oblique plane orientation)
        reslice_axes = reslice_cursor.GetResliceAxes()
        
        # Create reslice filter
        reslice = vtk.vtkImageReslice()
        reslice.SetInputData(image_data)
        reslice.SetOutputDimensionality(2)
        reslice.SetResliceAxes(reslice_axes)
        reslice.SetInterpolationModeToLinear()
        
        # Get the spacing and ensure proper output extent
        spacing = image_data.GetSpacing()
        dims = image_data.GetDimensions()
        
        # Set output extent (size of oblique plane)
        max_dim = max(dims[0] * spacing[0], dims[1] * spacing[1], dims[2] * spacing[2])
        output_spacing = min(spacing)
        output_size = int(max_dim / output_spacing)
        
        reslice.SetOutputSpacing(output_spacing, output_spacing, 1.0)
        reslice.SetOutputOrigin(0, 0, 0)
        reslice.SetOutputExtent(0, output_size - 1, 0, output_size - 1, 0, 0)
        reslice.Update()
        
        # Create lookup table for grayscale display
        lut = vtk.vtkLookupTable()
        scalar_range = image_data.GetScalarRange()
        lut.SetRange(scalar_range)
        lut.SetValueRange(0.0, 1.0)
        lut.SetSaturationRange(0.0, 0.0)
        lut.SetRampToLinear()
        lut.Build()
        
        # Map image through lookup table
        color_map = vtk.vtkImageMapToColors()
        color_map.SetLookupTable(lut)
        color_map.SetInputConnection(reslice.GetOutputPort())
        color_map.Update()
        
        # Set up image actor
        self.oblique_image_actor.GetMapper().SetInputConnection(color_map.GetOutputPort())
        self.oblique_image_actor.SetVisibility(True)
        
        # Add to renderer if not already there
        renderer = self.viewer.GetRenderer()
        if not renderer.HasViewProp(self.oblique_image_actor):
            renderer.AddActor(self.oblique_image_actor)
        
        # Reset camera to show entire oblique plane
        renderer.ResetCamera()
        self.viewer.Render()
    
    def set_oblique_angle(self, angle_degrees):
        """
        Set the rotation angle for the oblique plane.
        This rotates the plane around the current center point.
        
        Args:
            angle_degrees: Rotation angle in degrees
        """
        self.oblique_angle = angle_degrees
        
        if self.current_mode == "oblique":
            # Update the reslice axes based on new angle
            reslice_cursor = self.viewer.vtkBaseClass.resliceCursor
            
            # Create rotation transform
            transform = vtk.vtkTransform()
            transform.Translate(self.oblique_center)
            transform.RotateZ(angle_degrees)  # Rotate around Z axis
            transform.Translate(-self.oblique_center[0], -self.oblique_center[1], -self.oblique_center[2])
            
            # Apply transform to reslice axes
            matrix = transform.GetMatrix()
            reslice_cursor.GetResliceAxes().DeepCopy(matrix)
            
            # Update display
            self.show_oblique_plane()
    
    def set_oblique_center(self, x, y, z):
        """Set the center point for the oblique plane"""
        self.oblique_center = [x, y, z]
        reslice_cursor = self.viewer.vtkBaseClass.resliceCursor
        reslice_cursor.SetCenter(x, y, z)
        
        if self.current_mode == "oblique":
            self.show_oblique_plane()
    
    def connect_on_data(self, path):
        """Override to initialize display when data is loaded"""
        super().connect_on_data(path)
        
        # Initialize oblique center to image center
        image_data = self.viewer.vtkBaseClass.imageReader.GetOutput()
        if image_data:
            self.oblique_center = list(image_data.GetCenter())
        
        # Update initial display
        self.update_display()
