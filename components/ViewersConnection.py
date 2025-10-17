from vtk import *
from viewers.OrthoViewer import *
from .CommandSliceSelect import CommandSliceSelect

class ViewersConnection():
    
    # Constructor
    def __init__(self, vtkBaseClass:VtkBase) -> None:
        # Properties
        self.commandSliceSelect = CommandSliceSelect()
        self.orthogonal_viewers = []
        self.fourth_viewer = None
        self.vtkBaseClass = vtkBaseClass
        
    # Connect on data
    def connect_on_data(self):        
        if self.fourth_viewer:
            self.fourth_viewer.resliceCursorRep.SetLookupTable(self.orthogonal_viewers[0].grayscaleLut)

        self.orthogonal_viewers[1].resliceCursorRep.SetLookupTable(self.orthogonal_viewers[0].grayscaleLut)
        self.orthogonal_viewers[2].resliceCursorRep.SetLookupTable(self.orthogonal_viewers[0].grayscaleLut)

        for ortho_viewer in self.orthogonal_viewers:
            ortho_viewer.resliceCursorRep.SetLookupTable(self.orthogonal_viewers[0].grayscaleLut)

    # Add fourth viewer
    def add_fourth_viewer(self, fourth_viewer):
        self.fourth_viewer = fourth_viewer
    
    # Add orthogonal viewer
    def add_orthogonal_viewer(self, orthogonal_viewer):
        self.orthogonal_viewers.append(orthogonal_viewer)

    def connect_orthogonal_viewers(self):
        for i in range(len(self.orthogonal_viewers)):
            # Add observers to the reslice cursor to update the other viewers
            for j in range(len(self.orthogonal_viewers)):
                if i != j:
                    self.orthogonal_viewers[i].resliceCursorWidget.AddObserver(
                        vtk.vtkResliceCursorWidget.ResliceAxesChangedEvent,
                        self.orthogonal_viewers[j].update_slice_from_reslice_cursor
                    )