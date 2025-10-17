# PyQt5
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QFileDialog

# VTK
from viewers.QtOrthoViewer import *
from viewers.QtFourthViewer import QtFourthViewer
from components.VtkBase import VtkBase
from components.ViewersConnection import ViewersConnection
from viewers.ROIViewer import ROIViewer
# NEW: Import organ detection widget
from QtOrganDetectionWidget import QtOrganDetectionWidget

# Main Window
class MainWindow(QtWidgets.QMainWindow):
    
    # Constructor
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MPR Viewer")
        self.setWindowIcon(QtGui.QIcon("icon.ico"))
        
        # Create a central widget and set the layout
        central_widget = QtWidgets.QWidget()
        central_layout = QtWidgets.QHBoxLayout()
        
        # Create the viewers
        self.vtkBaseClass = VtkBase()
        self.QtSagittalOrthoViewer = QtOrthoViewer(self.vtkBaseClass, SLICE_ORIENTATION_YZ, "Sagittal Plane - YZ")
        self.QtCoronalOrthoViewer = QtOrthoViewer(self.vtkBaseClass, SLICE_ORIENTATION_XZ, "Coronal Plane - XZ")
        self.QtAxialOrthoViewer = QtOrthoViewer(self.vtkBaseClass, SLICE_ORIENTATION_XY, "Axial Plane - XY")
        self.QtExtraViewer = QtFourthViewer(self.vtkBaseClass, SLICE_ORIENTATION_XY, label="Extra Viewer")

        self.ViewersConnection = ViewersConnection(self.vtkBaseClass)
        self.ViewersConnection.add_orthogonal_viewer(self.QtSagittalOrthoViewer.get_viewer())
        self.ViewersConnection.add_orthogonal_viewer(self.QtCoronalOrthoViewer.get_viewer())
        self.ViewersConnection.add_orthogonal_viewer(self.QtAxialOrthoViewer.get_viewer())
        self.ViewersConnection.add_orthogonal_viewer(self.QtExtraViewer.get_viewer())
        self.ViewersConnection.connect_orthogonal_viewers()

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

        # NEW: Add organ detection dock widget to the right side
        self.organ_detection_widget = QtOrganDetectionWidget(self.vtkBaseClass, parent=self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.organ_detection_widget)

        # Add menu bar
        self.create_menu()

        # Connect signals and slots
        self.connect()

        # Connect the slice changed signal to the organ detection widget
        self.QtAxialOrthoViewer.slice_changed.connect(self.organ_detection_widget.on_slice_changed)
        self.QtCoronalOrthoViewer.slice_changed.connect(self.organ_detection_widget.on_slice_changed)
        self.QtSagittalOrthoViewer.slice_changed.connect(self.organ_detection_widget.on_slice_changed)

        # ROI Viewer
        self.roi_viewer = ROIViewer(self, self.vtkBaseClass)
        self.roi_viewer.off()

    # Connect signals and slots         
    def connect(self):
        pass
    
    # Create the menu bar
    def create_menu(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        roi_menu = menu_bar.addMenu("ROI")

        open_action = QtWidgets.QAction("Open Image", self)
        open_action.setShortcut("Ctrl+o")
        open_folder_action = QtWidgets.QAction("Open DICOM", self)
        open_folder_action.setShortcut("Ctrl+f")
        self.toggle_roi_action = QtWidgets.QAction("Toggle ROI", self)
        self.toggle_roi_action.setCheckable(True)
        self.toggle_roi_action.setShortcut("Ctrl+r")
        self.set_roi_action = QtWidgets.QAction("Set ROI", self)
        self.set_roi_action.setShortcut("Ctrl+s")

        open_action.triggered.connect(self.open_data)
        open_folder_action.triggered.connect(self.open_folder)
        self.toggle_roi_action.triggered.connect(self.toggle_roi)
        self.set_roi_action.triggered.connect(self.set_roi)

        file_menu.addAction(open_action)
        file_menu.addAction(open_folder_action)
        roi_menu.addAction(self.toggle_roi_action)
        roi_menu.addAction(self.set_roi_action)

    def toggle_roi(self):
        if self.toggle_roi_action.isChecked():
            self.roi_viewer.on()
        else:
            self.roi_viewer.off()

    def set_roi(self):
        self.roi_viewer.set_roi()

        # ✨ NEW: Add menu option to show/hide organ detection panel
        view_menu = menu_bar.addMenu("View")
        toggle_detection_action = QtWidgets.QAction("Toggle Organ Detection Panel", self)
        toggle_detection_action.setCheckable(True)
        toggle_detection_action.setChecked(True)
        toggle_detection_action.triggered.connect(
            lambda checked: self.organ_detection_widget.setVisible(checked)
        )
        view_menu.addAction(toggle_detection_action)
    # Open data
    def open_data(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Image Files (*.nii *.nii.gz *.mhd)")
        if file_dialog.exec_():
            filenames = file_dialog.selectedFiles()
            if len(filenames) > 0:
                filename = filenames[0]
                try:
                    self.load_data(filename)
                    self.render_data()
                except Exception as e:
                    print(e)
                    QtWidgets.QMessageBox.critical(self, "Error", "Unable to open the image file.")

    def open_folder(self):
        folder_dialog = QFileDialog()
        folder_dialog.setFileMode(QFileDialog.Directory)
        folder_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        if folder_dialog.exec_():
            folder_path = folder_dialog.selectedFiles()[0]
            try:
                self.load_data(folder_path)
                self.render_data()
            except Exception as e:
                print(e)
                QtWidgets.QMessageBox.critical(self, "Error", "Unable to open the folder.")

    # Load the data
    def load_data(self, filename):
        self.vtkBaseClass.connect_on_data(filename)

        # Load the image into the correct viewer
        self.QtAxialOrthoViewer.connect_on_data(filename)
        self.QtCoronalOrthoViewer.connect_on_data(filename)
        self.QtSagittalOrthoViewer.connect_on_data(filename)

        self.QtExtraViewer.connect_on_data(filename)
        self.ViewersConnection.connect_on_data()

        # NEW: Notify organ detection widget that data is loaded
        self.organ_detection_widget.connect_on_data(filename)

    # Render the data
    def render_data(self):
        self.QtAxialOrthoViewer.render()
        self.QtCoronalOrthoViewer.render()
        self.QtSagittalOrthoViewer.render()
        self.QtExtraViewer.render()

    # Close the application
    def closeEvent(self, QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.QtAxialOrthoViewer.close()
        self.QtCoronalOrthoViewer.close()
        self.QtSagittalOrthoViewer.close()
        self.QtExtraViewer.close()
    
    # Exit the application  
    def exit(self):
        self.close()
