"""
TotalSegmentator inference engine for PyQt5 integration.
Simplified version of inference.py optimized for GUI use.
"""

import numpy as np
import torch
import tempfile
import shutil
from pathlib import Path
from totalsegmentator.python_api import totalsegmentator
import SimpleITK as sitk
from utils import check_device

# TotalSegmentator organ labels (major organs only)
ORGAN_LABELS = {
    1: "spleen", 2: "kidney_right", 3: "kidney_left", 4: "gallbladder",
    5: "liver", 6: "stomach", 7: "pancreas", 8: "adrenal_gland_right",
    9: "adrenal_gland_left", 10: "lung_upper_lobe_left", 11: "lung_lower_lobe_left",
    12: "lung_upper_lobe_right", 13: "lung_middle_lobe_right", 14: "lung_lower_lobe_right",
    15: "esophagus", 16: "trachea", 17: "thyroid_gland", 18: "small_bowel",
    19: "duodenum", 20: "colon", 21: "urinary_bladder", 22: "prostate",
    55: "heart", 56: "aorta", 57: "pulmonary_vein", 104: "brain"
}


class SliceOrganDetector:
    """Organ detector optimized for PyQt5 GUI integration."""

    def __init__(self, device=None, fast_mode=True):
        """
        Initialize detector.

        Args:
            device: torch.device (auto-detected if None)
            fast_mode: Use faster inference settings
        """
        self.device = device if device else check_device()
        self.fast_