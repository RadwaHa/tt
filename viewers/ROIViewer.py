import vtk

class ROIViewer:
    def __init__(self, main_app, vtk_base):
        self.main_app = main_app
        self.vtk_base = vtk_base
        self.box_widgets = []
        self.current_box_widget = None

        for i in range(3):
            box_widget = vtk.vtkBoxWidget()
            box_widget.SetInteractor(self.main_app.ViewersConnection.orthogonal_viewers[i].GetRenderWindow().GetInteractor())
            box_widget.SetPlaceFactor(1.25)
            box_widget.SetInputData(self.vtk_base.imageReader.GetOutput())
            box_widget.PlaceWidget()
            box_widget.On()
            box_widget.AddObserver("InteractionEvent", self.update_roi)
            self.box_widgets.append(box_widget)

    def update_roi(self, caller, event):
        self.current_box_widget = caller

        # Get the planes from the current box widget
        planes = vtk.vtkPlanes()
        self.current_box_widget.GetPlanes(planes)

        for box_widget in self.box_widgets:
            if box_widget != self.current_box_widget:
                box_widget.PlaceWidget(planes.GetBounds())

    def get_roi_bounds(self):
        if self.current_box_widget:
            planes = vtk.vtkPlanes()
            self.current_box_widget.GetPlanes(planes)
            return planes.GetBounds()
        return None

    def set_roi(self):
        bounds = self.get_roi_bounds()
        if bounds:
            print(f"ROI Bounds: {bounds}")

            # Extract the ROI data
            extract = vtk.vtkExtractVOI()
            extract.SetInputData(self.vtk_base.imageReader.GetOutput())
            extract.SetVOI(int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]), int(bounds[4]), int(bounds[5]))
            extract.Update()

            # Display the ROI in the extra viewer
            self.main_app.QtExtraViewer.get_viewer().image_actor.SetInputData(extract.GetOutput())
            self.main_app.QtExtraViewer.render()

    def on(self):
        for box_widget in self.box_widgets:
            box_widget.On()

    def off(self):
        for box_widget in self.box_widgets:
            box_widget.Off()