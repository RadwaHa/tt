from vtk import vtkResliceImageViewer, vtkResliceCursor

class ViewersConnection:
    def __init__(self, viewers):
        self.viewers = viewers
        self.reslice_cursor = vtkResliceCursor()
        self.reslice_cursor.SetThickMode(0)
        self.reslice_cursor.SetCenter(0, 0, 0)

    def connect(self):
        for viewer in self.viewers:
            viewer.viewer.SetResliceCursor(self.reslice_cursor)
            viewer.viewer.GetRenderer().SetRenderWindow(viewer.GetRenderWindow())

        for i in range(len(self.viewers)):
            for j in range(len(self.viewers)):
                if i != j:
                    self.viewers[i].viewer.GetResliceCursorWidget().AddObserver(
                        "ResliceAxesChangedEvent", self.viewers[j].viewer.Render)
