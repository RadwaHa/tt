# PyQt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog

# VTK
from viewers.QtOrthoViewer import QtOrthoViewer
from viewers.QtFourthViewer import QtFourthViewer
from viewers.ROIViewer import ROIViewer
from viewers.ReferenceLineManager import ReferenceLineManager
from components.VtkBase import VtkBase
from components.ViewersConnection import ViewersConnection

# Main Window
class MainWindow(QtWidgets.QMainWindow):
    
    # Constructor
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MPR Viewer with Outline and Oblique Modes")
        self.setWindowIcon(QtGui.QIcon("icon.ico"))
        
        # Initialize VTK base class
        self.vtkBaseClass = VtkBase()
        
        # Create a central widget and set the layout
        central_widget = QtWidgets.QWidget()
        central_layout = QtWidgets.QHBoxLayout()
        
        # Create the viewers
        self.QtAxialOrthoViewer = QtOrthoViewer(orientation=0, label="Axial Plane - XY")
        self.QtCoronalOrthoViewer = QtOrthoViewer(orientation=1, label="Coronal Plane - XZ")
        self.QtSagittalOrthoViewer = QtOrthoViewer(orientation=2, label="Sagittal Plane - YZ")
        self.QtExtraViewer = QtFourthViewer(label="Fourth Viewer - Outline/Oblique")
        
        # Initialize ViewersConnection
        self.ViewersConnection = ViewersConnection([
            self.QtAxialOrthoViewer,
            self.QtCoronalOrthoViewer,
            self.QtSagittalOrthoViewer
        ])
        
        # Create reference line manager for oblique mode
        self.ref_line_manager = ReferenceLineManager(self.QtExtraViewer)

        # Set up the main layout
        main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        left_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        left_splitter.addWidget(self.QtAxialOrthoViewer)
        left_splitter.addWidget(self.QtExtraViewer)
        
        right_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        right_splitter.addWidget(self.QtCoronalOrthoViewer)
        right_splitter.addWidget(self.QtSagittalOrthoViewer)

        main_splitter.addWidget(left_splitter)
        main_splitter.addWidget(right_splitter)

        # Set the central widget
        central_layout.addWidget(main_splitter)
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)

        # Add a status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

        # Add menu bar
        self.create_menu()

        # Connect signals and slots
        self.connect()

        # ROI Viewer
        self.roi_viewer = ROIViewer(self, self.vtkBaseClass)
        self.roi_viewer.off()
        
        # Connect mouse events for reference line interaction
        self._setup_reference_line_interactions()

    def _setup_reference_line_interactions(self):
        """Setup mouse event handlers for reference line manipulation"""
        # Connect to axial viewer
        axial_canvas = self.QtAxialOrthoViewer
        axial_canvas.mpl_connect('button_press_event', 
            lambda event: self.ref_line_manager.handle_mouse_press(event, 'axial'))
        axial_canvas.mpl_connect('motion_notify_event', 
            lambda event: self.ref_line_manager.handle_mouse_motion(event, 'axial', axial_canvas))
        axial_canvas.mpl_connect('button_release_event', 
            lambda event: self.ref_line_manager.handle_mouse_release(event, 'axial'))
        
        # Connect to coronal viewer
        coronal_canvas = self.QtCoronalOrthoViewer
        coronal_canvas.mpl_connect('button_press_event', 
            lambda event: self.ref_line_manager.handle_mouse_press(event, 'coronal'))
        coronal_canvas.mpl_connect('motion_notify_event', 
            lambda event: self.ref_line_manager.handle_mouse_motion(event, 'coronal', coronal_canvas))
        coronal_canvas.mpl_connect('button_release_event', 
            lambda event: self.ref_line_manager.handle_mouse_release(event, 'coronal'))
        
        # Connect to sagittal viewer
        sagittal_canvas = self.QtSagittalOrthoViewer
        sagittal_canvas.mpl_connect('button_press_event', 
            lambda event: self.ref_line_manager.handle_mouse_press(event, 'sagittal'))
        sagittal_canvas.mpl_connect('motion_notify_event', 
            lambda event: self.ref_line_manager.handle_mouse_motion(event, 'sagittal', sagittal_canvas))
        sagittal_canvas.mpl_connect('button_release_event', 
            lambda event: self.ref_line_manager.handle_mouse_release(event, 'sagittal'))
