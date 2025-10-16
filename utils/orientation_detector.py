import numpy as np

class OrientationDetector:
    def __init__(self, simulated_orientation="Axial"):
        """
        Initializes the OrientationDetector.
        In a real implementation, this class would load a pre-trained model.
        For now, it simulates the model's behavior.
        """
        self.simulated_orientation = simulated_orientation

    def predict_orientation(self, image_data):
        """
        Simulates the prediction of the orientation of the given image data.
        """
        return self.simulated_orientation