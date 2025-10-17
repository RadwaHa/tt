"""
PyQt5 Widget for TotalSegmentator Organ Detection.
This widget integrates seamlessly with your existing MPR viewer.

Usage in app.py:
    from QtOrganDetectionWidget import QtOrganDetectionWidget
    self.organ_detection_widget = QtOrganDetectionWidget(self.vtkBaseClass)
    self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.organ_detection_widget)
"""

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
from pathlib import Path
import vtk

from inference_engine import SliceOrganDetector
from utils.helpers import check_device, save_results


class DetectionWorker(QThread):
    """
    Background thread for running organ detection without freezing the GUI.
    Emits signals to update the UI with progress and results.
    """
    progress = pyqtSignal(int, str)  # (percentage, message)
    finished = pyqtSignal(list)  # List of detection results
    error = pyqtSignal(str)  # Error message

    def __init__(self, detector, images, filenames):
        super().__init__()
        self.detector = detector
        self.images = images
        self.filenames = filenames

    def run(self):
        """Run detection in background thread."""
        try:
            self.progress.emit(10, "Initializing detector...")
            results = self.detector.detect_organs_in_slices(self.images, self.filenames)
            self.progress.emit(100, "Detection complete!")
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


from PyQt5.QtCore import pyqtSignal

class QtOrganDetectionWidget(QtWidgets.QDockWidget):
    """
    Dock widget for organ detection that integrates with MPR viewer.
    Provides controls for running TotalSegmentator and visualizing results.
    """
    detection_completed = pyqtSignal(list)

    def __init__(self, vtkBaseClass, parent=None):
        super().__init__("🔬 Organ Detection (TotalSegmentator)", parent)

        # Store reference to VTK base class (shares data with MPR viewer)
        self.vtkBaseClass = vtkBaseClass
        self.detector = None
        self.results = None
        self.current_slice_idx = 0
        self.images_cache = None
        self.overlay_actors = {}  # Store overlay actors for each viewer

        # Set dock widget properties
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable |
                         QtWidgets.QDockWidget.DockWidgetFloatable)

        # Create main widget and layout
        main_widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setWidget(main_widget)

        # Build UI sections
        self._create_device_info_section(main_layout)
        self._create_detection_controls(main_layout)
        self._create_results_section(main_layout)
        self._create_save_section(main_layout)

        # Add stretch to push everything to top
        main_layout.addStretch()

        # Check device on startup
        self.device = check_device()

    def _create_device_info_section(self, parent_layout):
        """Create section showing GPU/CPU status."""
        group = QtWidgets.QGroupBox("⚙️ System Status")
        layout = QtWidgets.QVBoxLayout()

        self.device_label = QtWidgets.QLabel("Checking device...")
        self.device_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.device_label)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_detection_controls(self, parent_layout):
        """Create controls for running detection."""
        group = QtWidgets.QGroupBox("🎯 Detection Controls")
        layout = QtWidgets.QVBoxLayout()

        # Fast mode checkbox
        self.fast_mode_checkbox = QtWidgets.QCheckBox("Fast Mode (recommended)")
        self.fast_mode_checkbox.setChecked(True)
        self.fast_mode_checkbox.setToolTip("Uses faster inference with slightly lower accuracy")
        layout.addWidget(self.fast_mode_checkbox)

        # Slice range selection
        slice_layout = QtWidgets.QHBoxLayout()
        slice_layout.addWidget(QtWidgets.QLabel("Process slices:"))

        self.slice_range_combo = QtWidgets.QComboBox()
        self.slice_range_combo.addItems(["All slices", "Current slice only", "Custom range"])
        self.slice_range_combo.setToolTip("Choose which slices to process")
        slice_layout.addWidget(self.slice_range_combo)
        layout.addLayout(slice_layout)

        # Run detection button
        self.run_button = QtWidgets.QPushButton("▶ Run Detection")
        self.run_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.run_button.clicked.connect(self.run_detection)
        self.run_button.setEnabled(False)
        layout.addWidget(self.run_button)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QtWidgets.QLabel("Load DICOM data to begin")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_results_section(self, parent_layout):
        """Create section for displaying detection results."""
        group = QtWidgets.QGroupBox("📊 Detection Results")
        layout = QtWidgets.QVBoxLayout()

        # Slice navigator
        nav_layout = QtWidgets.QHBoxLayout()
        nav_layout.addWidget(QtWidgets.QLabel("Slice:"))

        self.slice_spinbox = QtWidgets.QSpinBox()
        self.slice_spinbox.setMinimum(0)
        self.slice_spinbox.setMaximum(0)
        self.slice_spinbox.valueChanged.connect(self.on_slice_changed)
        nav_layout.addWidget(self.slice_spinbox)

        self.prev_slice_btn = QtWidgets.QPushButton("◀ Prev")
        self.prev_slice_btn.clicked.connect(lambda: self.slice_spinbox.setValue(self.slice_spinbox.value() - 1))
        nav_layout.addWidget(self.prev_slice_btn)

        self.next_slice_btn = QtWidgets.QPushButton("Next ▶")
        self.next_slice_btn.clicked.connect(lambda: self.slice_spinbox.setValue(self.slice_spinbox.value() + 1))
        nav_layout.addWidget(self.next_slice_btn)

        layout.addLayout(nav_layout)

        # Results text display
        self.results_text = QtWidgets.QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        self.results_text.setPlaceholderText("Run detection to see results...")
        layout.addWidget(self.results_text)

        # Show/hide overlay controls
        overlay_layout = QtWidgets.QHBoxLayout()
        self.show_overlay_checkbox = QtWidgets.QCheckBox("Show overlay on viewers")
        self.show_overlay_checkbox.setChecked(True)
        self.show_overlay_checkbox.stateChanged.connect(self.toggle_overlay_visibility)
        overlay_layout.addWidget(self.show_overlay_checkbox)

        self.overlay_opacity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.overlay_opacity_slider.setMinimum(0)
        self.overlay_opacity_slider.setMaximum(100)
        self.overlay_opacity_slider.setValue(50)
        self.overlay_opacity_slider.setToolTip("Overlay opacity")
        self.overlay_opacity_slider.valueChanged.connect(self.update_overlay_opacity)
        overlay_layout.addWidget(self.overlay_opacity_slider)

        layout.addLayout(overlay_layout)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _create_save_section(self, parent_layout):
        """Create section for saving results."""
        group = QtWidgets.QGroupBox("💾 Export Results")
        layout = QtWidgets.QVBoxLayout()

        self.save_button = QtWidgets.QPushButton("Save Results (CSV + Masks)")
        self.save_button.clicked.connect(self.save_detection_results)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        group.setLayout(layout)
        parent_layout.addWidget(group)

    def connect_on_data(self, filename):
        """
        Called when new DICOM data is loaded in the MPR viewer.
        Extracts slice data and enables detection controls.

        Args:
            filename (str): Path to loaded MHD/DICOM file
        """
        try:
            # Get image data from VTK reader
            if self.vtkBaseClass.reader is None:
                return

            # Extract all slices from the 3D volume
            self.images_cache = self._extract_slices_from_vtk()

            if self.images_cache:
                num_slices = len(self.images_cache)
                self.run_button.setEnabled(True)
                self.status_label.setText(f"✓ Ready: {num_slices} slices loaded")
                self.status_label.setStyleSheet("color: green; padding: 5px;")

                # Update slice navigator
                self.slice_spinbox.setMaximum(num_slices - 1)
                self.slice_spinbox.setValue(num_slices // 2)  # Start at middle

                # Update device info
                import torch
                if torch.cuda.is_available():
                    gpu_name = torch.cuda.get_device_name(0)
                    vram = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
                    self.device_label.setText(f"✓ GPU: {gpu_name}\nVRAM: {vram:.1f} GB")
                    self.device_label.setStyleSheet("color: green; padding: 5px; font-weight: bold;")
                else:
                    self.device_label.setText("⚠️ CPU Mode (Slow)\nRecommend: Use GPU")
                    self.device_label.setStyleSheet("color: orange; padding: 5px;")
            else:
                self.status_label.setText("❌ Failed to extract slices")
                self.status_label.setStyleSheet("color: red; padding: 5px;")

        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red; padding: 5px;")

    def _extract_slices_from_vtk(self):
        """
        Extract 2D slices from VTK 3D image data.
        Returns list of numpy arrays (one per slice).
        """
        try:
            # Get the VTK image data
            image_data = self.vtkBaseClass.reader.GetOutput()
            dims = image_data.GetDimensions()

            # Convert VTK image to numpy array
            from vtk.util import numpy_support
            vtk_array = image_data.GetPointData().GetScalars()
            numpy_array = numpy_support.vtk_to_numpy(vtk_array)

            # Reshape to 3D (assuming axial slices along Z axis)
            numpy_array = numpy_array.reshape(dims[2], dims[1], dims[0])

            # Extract each slice
            slices = []
            for z in range(dims[2]):
                slice_data = numpy_array[z, :, :].astype(np.float32)
                slices.append(slice_data)

            return slices

        except Exception as e:
            print(f"Error extracting slices: {e}")
            return None

    def run_detection(self):
        """Run TotalSegmentator detection in background thread."""
        if not self.images_cache:
            QtWidgets.QMessageBox.warning(self, "No Data", "Please load DICOM data first")
            return

        # Initialize detector if needed
        if self.detector is None:
            fast_mode = self.fast_mode_checkbox.isChecked()
            self.detector = SliceOrganDetector(device=self.device, fast_mode=fast_mode)

        # Determine which slices to process
        slice_mode = self.slice_range_combo.currentText()
        if slice_mode == "Current slice only":
            images_to_process = [self.images_cache[self.current_slice_idx]]
            filenames = [f"slice_{self.current_slice_idx:04d}"]
        else:  # "All slices" or "Custom range"
            images_to_process = self.images_cache
            filenames = [f"slice_{i:04d}" for i in range(len(self.images_cache))]

        # Disable controls during processing
        self.run_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("🔄 Running detection...")
        self.status_label.setStyleSheet("color: blue; padding: 5px;")

        # Create and start worker thread
        self.worker = DetectionWorker(self.detector, images_to_process, filenames)
        self.worker.progress.connect(self.on_detection_progress)
        self.worker.finished.connect(self.on_detection_finished)
        self.worker.error.connect(self.on_detection_error)
        self.worker.start()

    def on_detection_progress(self, percentage, message):
        """Update progress bar during detection."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def on_detection_finished(self, results):
        """Handle detection completion."""
        self.results = results
        self.progress_bar.setVisible(False)
        self.run_button.setEnabled(True)
        self.save_button.setEnabled(True)

        if results:
            total_organs = sum(len(r['organs']) for r in results)
            self.status_label.setText(f"✓ Complete: Found {total_organs} organ detections across {len(results)} slices")
            self.status_label.setStyleSheet("color: green; padding: 5px; font-weight: bold;")

            # Display results for current slice
            self.display_results_for_slice(self.current_slice_idx)

            # Emit the detection completed signal
            self.detection_completed.emit(self.results)

            # Add overlays to viewers if enabled
            if self.show_overlay_checkbox.isChecked():
                self.update_overlay_on_viewers()
        else:
            self.status_label.setText("⚠️ No organs detected")
            self.status_label.setStyleSheet("color: orange; padding: 5px;")

    def on_detection_error(self, error_msg):
        """Handle detection error."""
        self.progress_bar.setVisible(False)
        self.run_button.setEnabled(True)
        self.status_label.setText(f"❌ Error: {error_msg}")
        self.status_label.setStyleSheet("color: red; padding: 5px;")
        QtWidgets.QMessageBox.critical(self, "Detection Error", error_msg)

    def on_slice_changed(self, slice_idx):
        """Handle slice navigation."""
        self.current_slice_idx = slice_idx
        if self.results:
            self.display_results_for_slice(slice_idx)
            if self.show_overlay_checkbox.isChecked():
                self.update_overlay_on_viewers()

    def display_results_for_slice(self, slice_idx):
        """Display detection results for a specific slice."""
        if not self.results or slice_idx >= len(self.results):
            return

        result = self.results[slice_idx]

        # Format results as HTML
        html = f"<b>Slice {slice_idx + 1} of {len(self.results)}</b><br>"
        html += f"<b>Filename:</b> {result['filename']}<br>"
        html += f"<b>Organs detected:</b> {result['num_organs']}<br><br>"

        if result['organs']:
            html += "<b>Detected organs:</b><ul>"
            for organ in result['organs']:
                html += f"<li style='color: #2196F3;'>{organ.replace('_', ' ').title()}</li>"
            html += "</ul>"
        else:
            html += "<i style='color: #999;'>No organs detected in this slice</i>"

        html += f"<br><b>Confidence:</b> {result['confidence']:.2f}"

        self.results_text.setHtml(html)

    def update_overlay_on_viewers(self):
        """Add segmentation overlays to the MPR viewers (placeholder for VTK integration)."""
        # TODO: Implement VTK overlay rendering on your orthogonal viewers
        # This requires accessing your QtOrthoViewer instances and adding mask actors
        pass

    def toggle_overlay_visibility(self, state):
        """Show/hide overlays on viewers."""
        # TODO: Implement overlay visibility toggle
        pass

    def update_overlay_opacity(self, value):
        """Update overlay transparency."""
        # TODO: Implement opacity adjustment
        pass

    def save_detection_results(self):
        """Save results to CSV and mask images."""
        if not self.results:
            return

        # Ask user for output directory
        output_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QtWidgets.QFileDialog.ShowDirsOnly
        )

        if not output_dir:
            return

        try:
            # Prepare data for saving
            results_data = []
            masks_to_save = []

            for result in self.results:
                for organ in result['organs']:
                    results_data.append({
                        'filename': result['filename'],
                        'slice_index': result['slice_index'],
                        'organ': organ,
                        'confidence': result['confidence'],
                        'mask_path': f"masks/{Path(result['filename']).stem}_{organ}_mask.png"
                    })

                    masks_to_save.append({
                        'filename': f"{Path(result['filename']).stem}_{organ}",
                        'mask': result['masks'][organ]
                    })

            # Save using utils function
            csv_path, masks_dir = save_results(output_dir, results_data, masks_to_save)

            QtWidgets.QMessageBox.information(
                self,
                "Results Saved",
                f"Results saved successfully!\n\nCSV: {csv_path}\nMasks: {masks_dir}"
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save Error", f"Failed to save results:\n{str(e)}")