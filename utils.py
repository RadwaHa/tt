"""
Utility functions for DICOM loading, device detection, and result saving.
This module handles all the helper operations needed by the main inference and GUI.
"""

import os
import torch
import pydicom
import numpy as np
import SimpleITK as sitk
from pathlib import Path
from datetime import datetime
import pandas as pd
from PIL import Image
import json


def check_device():
    """
    Check if CUDA GPU is available and print device information.
    Returns the appropriate torch device and prints warnings if on CPU.

    Returns:
        torch.device: Device to use for inference (cuda or cpu)
    """
    if torch.cuda.is_available():
        device = torch.device("cuda")
        gpu_name = torch.cuda.get_device_name(0)
        # Get VRAM in GB
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"✓ GPU detected: {gpu_name}")
        print(f"✓ VRAM: {vram_gb:.1f} GB")
        print(f"✓ Using GPU acceleration for inference")
        return device
    else:
        device = torch.device("cpu")
        print("\n" + "=" * 70)
        print("⚠️  WARNING: No CUDA GPU detected!")
        print("⚠️  Running on CPU — inference may be VERY slow (10-100x slower)")
        print("⚠️  Recommendations:")
        print("   • Use Google Colab with GPU runtime (free T4 GPU)")
        print("   • Or use local NVIDIA GPU (RTX 3060+ with >=6GB VRAM)")
        print("=" * 70 + "\n")
        return device


def load_dicom_slice(dicom_path):
    """
    Load a single DICOM slice and return as numpy array with metadata.

    Args:
        dicom_path (str): Path to DICOM file

    Returns:
        tuple: (image_array, metadata_dict)
    """
    try:
        # Read DICOM file using pydicom
        dcm = pydicom.dcmread(dicom_path)

        # Get pixel array and apply rescale if available
        img_array = dcm.pixel_array.astype(np.float32)

        # Apply DICOM windowing (rescale slope and intercept)
        if hasattr(dcm, 'RescaleSlope') and hasattr(dcm, 'RescaleIntercept'):
            img_array = img_array * dcm.RescaleSlope + dcm.RescaleIntercept

        # Extract useful metadata
        metadata = {
            'PatientID': getattr(dcm, 'PatientID', 'Unknown'),
            'SeriesDescription': getattr(dcm, 'SeriesDescription', 'Unknown'),
            'SliceLocation': getattr(dcm, 'SliceLocation', None),
            'InstanceNumber': getattr(dcm, 'InstanceNumber', None),
        }

        return img_array, metadata

    except Exception as e:
        print(f"Error loading DICOM {dicom_path}: {e}")
        return None, None


def load_dicom_folder(folder_path):
    """
    Load all DICOM files from a folder and sort by slice location/instance number.

    Args:
        folder_path (str): Path to folder containing DICOM files

    Returns:
        tuple: (list of image arrays, list of filenames, list of metadata)
    """
    folder = Path(folder_path)
    dicom_files = sorted(folder.glob("*.dcm"))

    if not dicom_files:
        # Try without extension
        dicom_files = [f for f in folder.iterdir() if f.is_file()]

    images = []
    filenames = []
    metadata_list = []

    for dcm_file in dicom_files:
        img, meta = load_dicom_slice(str(dcm_file))
        if img is not None:
            images.append(img)
            filenames.append(dcm_file.name)
            metadata_list.append(meta)

    # Sort by instance number or slice location if available
    if metadata_list and metadata_list[0].get('InstanceNumber'):
        sorted_indices = sorted(range(len(metadata_list)),
                                key=lambda i: metadata_list[i].get('InstanceNumber', 0))
        images = [images[i] for i in sorted_indices]
        filenames = [filenames[i] for i in sorted_indices]
        metadata_list = [metadata_list[i] for i in sorted_indices]

    print(f"✓ Loaded {len(images)} DICOM slices from {folder_path}")
    return images, filenames, metadata_list


def normalize_image_for_display(img_array):
    """
    Normalize image array to 0-255 range for display.
    Handles different intensity ranges (CT, MRI, etc.)

    Args:
        img_array (np.ndarray): Input image array

    Returns:
        np.ndarray: Normalized uint8 array
    """
    # Clip outliers (improves visualization)
    p2, p98 = np.percentile(img_array, (2, 98))
    img_normalized = np.clip(img_array, p2, p98)

    # Scale to 0-255
    img_normalized = (img_normalized - img_normalized.min()) / (img_normalized.max() - img_normalized.min() + 1e-8)
    img_normalized = (img_normalized * 255).astype(np.uint8)

    return img_normalized


def create_overlay(image, mask, alpha=0.5, color=[255, 0, 0]):
    """
    Create an overlay of segmentation mask on the original image.

    Args:
        image (np.ndarray): Original grayscale image (H, W)
        mask (np.ndarray): Binary mask (H, W)
        alpha (float): Transparency of overlay (0-1)
        color (list): RGB color for mask overlay

    Returns:
        np.ndarray: RGB image with overlay (H, W, 3)
    """
    # Normalize image to 0-255 if needed
    if image.max() > 255 or image.dtype != np.uint8:
        image = normalize_image_for_display(image)

    # Create RGB image from grayscale
    img_rgb = np.stack([image, image, image], axis=-1)

    # Create colored mask
    mask_rgb = np.zeros_like(img_rgb)
    mask_rgb[mask > 0] = color

    # Blend image and mask
    overlay = img_rgb.copy()
    overlay[mask > 0] = (
            alpha * mask_rgb[mask > 0] + (1 - alpha) * img_rgb[mask > 0]
    ).astype(np.uint8)

    return overlay


def save_results(output_dir, results_data, masks=None):
    """
    Save detection results to CSV and optionally save mask images.

    Args:
        output_dir (str): Directory to save results
        results_data (list): List of dicts with detection results
        masks (list): Optional list of mask arrays to save

    Returns:
        tuple: (csv_path, masks_dir)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create timestamped subdirectory for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_path / f"run_{timestamp}"
    run_dir.mkdir(exist_ok=True)

    # Save CSV with detection results
    df = pd.DataFrame(results_data)
    csv_path = run_dir / "detections.csv"
    df.to_csv(csv_path, index=False)
    print(f"✓ Saved detections to: {csv_path}")

    # Save masks if provided
    masks_dir = None
    if masks:
        masks_dir = run_dir / "masks"
        masks_dir.mkdir(exist_ok=True)

        for i, mask_data in enumerate(masks):
            mask_array = mask_data['mask']
            filename = mask_data['filename']

            # Save as PNG
            mask_img = Image.fromarray((mask_array * 255).astype(np.uint8))
            mask_path = masks_dir / f"{Path(filename).stem}_mask.png"
            mask_img.save(mask_path)

        print(f"✓ Saved {len(masks)} masks to: {masks_dir}")

    # Save run log
    log_data = {
        'timestamp': timestamp,
        'num_slices': len(results_data),
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'results': results_data
    }
    log_path = run_dir / "run_log.json"
    with open(log_path, 'w') as f:
        json.dump(log_data, f, indent=2)

    return csv_path, masks_dir


def estimate_vram_needed(num_slices, slice_size=(512, 512)):
    """
    Estimate VRAM needed for processing given number of slices.
    This is a rough estimate for planning batch sizes.

    Args:
        num_slices (int): Number of slices to process
        slice_size (tuple): Size of each slice (H, W)

    Returns:
        float: Estimated VRAM in GB
    """
    # Rough estimate: ~50MB per 512x512 slice with model overhead
    pixels_per_slice = slice_size[0] * slice_size[1]
    base_slice_mem = pixels_per_slice / (512 * 512) * 50  # MB
    model_overhead = 500  # MB for model weights

    total_mb = base_slice_mem * num_slices + model_overhead
    return total_mb / 1024  # Convert to GB