class CommandSliceSelect(object):
    def __init__(self):
        self.resliceCursorWidgets = [None, None, None]
        self.imagePlaneWidgets = [None, None, None]
        self.resliceCursor = None
        self.sliders = [None, None, None]

    def __call__(self, caller, event):
        if event == "ResliceAxesChangedEvent":
            self.reslice_axes_changed(caller)
        elif event == "EndInteractionEvent":
            self.end_interaction(caller)

    def reslice_axes_changed(self, caller):
        if caller == self.resliceCursorWidgets[0]:
            self.update_reslice(self.resliceCursorWidgets[1], self.resliceCursorWidgets[2])
        elif caller == self.resliceCursorWidgets[1]:
            self.update_reslice(self.resliceCursorWidgets[0], self.resliceCursorWidgets[2])
        elif caller == self.resliceCursorWidgets[2]:
            self.update_reslice(self.resliceCursorWidgets[0], self.resliceCursorWidgets[1])

    def end_interaction(self, caller):
        for i in range(3):
            if caller == self.imagePlaneWidgets[i]:
                self.resliceCursor.SetCenter(self.imagePlaneWidgets[i].GetPolyData().GetPoint(0))
                self.update_reslice(self.resliceCursorWidgets[(i + 1) % 3], self.resliceCursorWidgets[(i + 2) % 3])

    def update_reslice(self, widget1, widget2):
        widget1.Render()
        widget2.Render()
        for i in range(3):
            slice_val = self.resliceCursor.GetImage().GetBounds()[i * 2 + int(self.resliceCursor.GetImage().GetExtent()[i * 2] == self.resliceCursor.GetImage().GetExtent()[i * 2 + 1])]
            self.sliders[i].setValue(int(slice_val))