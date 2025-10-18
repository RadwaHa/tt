"""
Reference Line Manager for Oblique Plane Control
Handles interactive rotation and translation of reference lines in orthogonal views
"""

import vtk
import numpy as np


class ReferenceLineManager:
    """
    Manages reference lines in orthogonal views that control oblique plane orientation.
    Users can rotate and translate these lines to define custom oblique planes.
    """
    
    def __init__(self, fourth_viewer):
        """
        Initialize reference line manager.
        
        Args:
            fourth_viewer: QtFourthViewer instance to update
        """
        self.fourth_viewer = fourth_viewer
        
        # Reference lines for each orthogonal view
        self.ref_lines = {
            'axial': None,
            'coronal': None,
            'sagittal': None
        }
        
        # Line properties
        self.line_angle = 0  # Current rotation angle (degrees)
        self.line_center = [0, 0]  # Center point in 2D view
        
        # Control points for interaction
        self.control_points = {
            'axial': {'left': None, 'right': None, 'center': None},
            'coronal': {'left': None, 'right': None, 'center': None},
            'sagittal': {'left': None, 'right': None, 'center': None}
        }
        
        # Interaction state
        self.is_dragging = False
        self.drag_type = None  # 'rotate', 'translate'
        self.active_view = None
        self.drag_start_pos = None
    
    def create_reference_lines(self, viewers):
        """
        Create reference lines in all orthogonal viewers.
        
        Args:
            viewers: Dictionary with keys 'axial', 'coronal', 'sagittal' containing QtOrthoViewer instances
        """
        for view_name, viewer in viewers.items():
            self._create_line_in_view(view_name, viewer)
    
    def _create_line_in_view(self, view_name, viewer):
        """Create reference line and control points in a specific view"""
        renderer = viewer.GetRenderer()
        
        # Create line actor
        line_source = vtk.vtkLineSource()
        line_mapper = vtk.vtkPolyDataMapper()
        line_mapper.SetInputConnection(line_source.GetOutputPort())
        
        line_actor = vtk.vtkActor()
        line_actor.SetMapper(line_mapper)
        line_actor.GetProperty().SetColor(0.0, 1.0, 0.0)  # Green
        line_actor.GetProperty().SetLineWidth(3)
        
        renderer.AddActor(line_actor)
        self.ref_lines[view_name] = {
            'source': line_source,
            'actor': line_actor
        }
        
        # Create control points
        self._create_control_points(view_name, renderer)
        
        # Update line position
        self._update_line_geometry(view_name, viewer)
    
    def _create_control_points(self, view_name, renderer):
        """Create interactive control points (left, right, center) for a line"""
        colors = {
            'left': [1.0, 0.0, 0.0],    # Red
            'right': [1.0, 1.0, 0.0],   # Yellow
            'center': [1.0, 0.0, 1.0]   # Magenta
        }
        
        for point_name, color in colors.items():
            # Create sphere for control point
            sphere = vtk.vtkSphereSource()
            sphere.SetRadius(5.0)
            sphere.SetThetaResolution(16)
            sphere.SetPhiResolution(16)
            
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(sphere.GetOutputPort())
            
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(color)
            
            renderer.AddActor(actor)
            self.control_points[view_name][point_name] = {
                'source': sphere,
                'actor': actor
            }
    
    def _update_line_geometry(self, view_name, viewer):
        """Update line and control point positions based on current angle and center"""
        if view_name not in self.ref_lines or not self.ref_lines[view_name]:
            return
        
        # Get image dimensions for this view
        image_data = viewer.vtkBaseClass.imageReader.GetOutput()
        if not image_data:
            return
        
        dims = image_data.GetDimensions()
        bounds = image_data.GetBounds()
        
        # Calculate line endpoints based on angle
        angle_rad = np.radians(self.line_angle)
        
        # Get view-specific center
        if self.line_center == [0, 0]:
            # Initialize to image center
            if view_name == 'axial':
                self.line_center = [(bounds[0] + bounds[1]) / 2, (bounds[2] + bounds[3]) / 2]
            elif view_name == 'coronal':
                self.line_center = [(bounds[0] + bounds[1]) / 2, (bounds[4] + bounds[5]) / 2]
            else:  # sagittal
                self.line_center = [(bounds[2] + bounds[3]) / 2, (bounds[4] + bounds[5]) / 2]
        
        center_x, center_y = self.line_center
        
        # Calculate line length (should span the view)
        max_dim = max(dims[0], dims[1], dims[2])
        line_length = max_dim * 0.8
        
        # Calculate line endpoints
        half_length = line_length / 2
        x1 = center_x - half_length * np.cos(angle_rad)
        y1 = center_y - half_length * np.sin(angle_rad)
        x2 = center_x + half_length * np.cos(angle_rad)
        y2 = center_y + half_length * np.sin(angle_rad)
        
        # Update line
        line_source = self.ref_lines[view_name]['source']
        line_source.SetPoint1(x1, y1, 0)
        line_source.SetPoint2(x2, y2, 0)
        line_source.Update()
        
        # Update control points
        control_offset = max_dim * 0.05
        
        # Left control point (rotate handle)
        left_x = center_x - control_offset * np.cos(angle_rad)
        left_y = center_y - control_offset * np.sin(angle_rad)
        self.control_points[view_name]['left']['actor'].SetPosition(left_x, left_y, 0)
        
        # Right control point (rotate handle)
        right_x = center_x + control_offset * np.cos(angle_rad)
        right_y = center_y + control_offset * np.sin(angle_rad)
        self.control_points[view_name]['right']['actor'].SetPosition(right_x, right_y, 0)
        
        # Center control point (translate handle)
        self.control_points[view_name]['center']['actor'].SetPosition(center_x, center_y, 0)
    
    def handle_mouse_press(self, event, view_name):
        """
        Handle mouse press event to start dragging.
        
        Args:
            event: Mouse event with xdata, ydata
            view_name: Name of the view ('axial', 'coronal', 'sagittal')
        
        Returns:
            bool: True if interaction started, False otherwise
        """
        if event.xdata is None or event.ydata is None:
            return False
        
        click_pos = [event.xdata, event.ydata]
        click_tolerance = 15.0
        
        # Check if clicking on control points
        for point_name, point_data in self.control_points[view_name].items():
            point_pos = point_data['actor'].GetPosition()[:2]
            distance = np.sqrt((click_pos[0] - point_pos[0])**2 + (click_pos[1] - point_pos[1])**2)
            
            if distance < click_tolerance:
                self.is_dragging = True
                self.active_view = view_name
                self.drag_start_pos = click_pos
                
                if point_name in ['left', 'right']:
                    self.drag_type = 'rotate'
                else:  # center
                    self.drag_type = 'translate'
                
                return True
        
        return False
    
    def handle_mouse_motion(self, event, view_name, viewer):
        """
        Handle mouse motion during dragging.
        
        Args:
            event: Mouse event with xdata, ydata
            view_name: Name of the view
            viewer: QtOrthoViewer instance
        """
        if not self.is_dragging or view_name != self.active_view:
            return
        
        if event.xdata is None or event.ydata is None:
            return
        
        current_pos = [event.xdata, event.ydata]
        
        if self.drag_type == 'rotate':
            # Calculate new angle based on mouse position relative to center
            dx = current_pos[0] - self.line_center[0]
            dy = current_pos[1] - self.line_center[1]
            self.line_angle = np.degrees(np.arctan2(dy, dx))
            
        elif self.drag_type == 'translate':
            # Move center point
            delta_x = current_pos[0] - self.drag_start_pos[0]
            delta_y = current_pos[1] - self.drag_start_pos[1]
            self.line_center[0] += delta_x
            self.line_center[1] += delta_y
            self.drag_start_pos = current_pos
        
        # Update line geometry
        self._update_line_geometry(view_name, viewer)
        
        # Update oblique plane in fourth viewer
        self.update_oblique_plane()
        
        # Render
        viewer.Render()
    
    def handle_mouse_release(self, event, view_name):
        """Handle mouse release to end dragging"""
        if self.active_view == view_name:
            self.is_dragging = False
            self.drag_type = None
            self.active_view = None
            self.drag_start_pos = None
    
    def update_oblique_plane(self):
        """Update the oblique plane in fourth viewer based on current line parameters"""
        # Convert 2D line parameters to 3D oblique plane orientation
        self.fourth_viewer.set_oblique_angle(self.line_angle)
        
        # Update center point (convert 2D to 3D based on active view)
        # For simplicity, we keep the existing 3D center and only rotate
    
    def set_visibility(self, visible):
        """Show or hide reference lines and control points"""
        for view_name in self.ref_lines:
            if self.ref_lines[view_name]:
                self.ref_lines[view_name]['actor'].SetVisibility(visible)
            
            for point_data in self.control_points[view_name].values():
                if point_data:
                    point_data['actor'].SetVisibility(visible)
    
    def set_angle(self, angle_degrees):
        """Set the rotation angle programmatically"""
        self.line_angle = angle_degrees
        
        # Update all views
        for view_name in self.ref_lines:
            if self.ref_lines[view_name]:
                self._update_line_geometry(view_name, None)
        
        self.update_oblique_plane()
