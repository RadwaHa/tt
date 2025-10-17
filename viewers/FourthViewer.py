from .OrthoViewer import *

class FourthViewer(OrthoViewer):
    def __init__(self, vtkBaseClass, orientation, label: str = "Fourth Viewer"):
        super().__init__(vtkBaseClass, orientation, label)
        self.outline_actor = None

    def show_outline(self, result):
        if self.outline_actor:
            self.renderer.RemoveActor(self.outline_actor)
            self.outline_actor = None

        if not result or not result['masks']:
            self.render()
            return

        mask = list(result['masks'].values())[0]

        vtk_image = vtk.vtkImageData()
        vtk_image.SetDimensions(mask.shape[1], mask.shape[0], 1)
        vtk_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                vtk_image.SetScalarComponentFromDouble(x, y, 0, 0, mask[y, x])

        marching_squares = vtk.vtkMarchingSquares()
        marching_squares.SetInputData(vtk_image)
        marching_squares.SetValue(0, 0.5)
        marching_squares.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(marching_squares.GetOutputPort())

        self.outline_actor = vtk.vtkActor()
        self.outline_actor.SetMapper(mapper)
        self.outline_actor.GetProperty().SetColor(1, 0, 0)
        self.renderer.AddActor(self.outline_actor)
        self.render()