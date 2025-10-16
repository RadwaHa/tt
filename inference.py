"""
Slice-level organ detection using TotalSegmentator.
This script performs organ segmentation on individual DICOM slices and identifies
which organs are present in each slice with bounding masks.

Can be run headlessly (no GUI) from command line.
"""

import argparse
import numpy as np
import torch
import tempfile
import shutil
from pathlib import Path
from totalsegmentator.python_api import totalsegmentator
import SimpleITK as sitk
from utils import (
    check_device,
    load_dicom_slice,
    load_dicom_folder,
    save_results,
    estimate_vram_needed
)

# TotalSegmentator organ labels (simplified set for common organs)
# Full list has 104 structures, we focus on major organs for clarity
ORGAN_LABELS = {
    1: "spleen", 2: "kidney_right", 3: "kidney_left", 4: "gallbladder",
    5: "liver", 6: "stomach", 7: "pancreas", 8: "adrenal_gland_right",
    9: "adrenal_gland_left", 10: "lung_upper_lobe_left", 11: "lung_lower_lobe_left",
    12: "lung_upper_lobe_right", 13: "lung_middle_lobe_right", 14: "lung_lower_lobe_right",
    15: "esophagus", 16: "trachea", 17: "thyroid_gland", 18: "small_bowel",
    19: "duodenum", 20: "colon", 21: "urinary_bladder", 22: "prostate",
    23: "kidney_cyst_left", 24: "kidney_cyst_right", 55: "heart",
    56: "aorta", 57: "pulmonary_vein", 58: "brachiocephalic_trunk",
    104: "brain"
}


class SliceOrganDetector:
    """
    Main class for performing slice-level organ detection.
    Uses TotalSegmentator to segment organs and extract per-slice information.
    """

    def __init__(self, device=None, fast_mode=True):
        """
        Initialize the detector.

        Args:
            device (torch.device): Device to run inference on (auto-detected if None)
            fast_mode (bool): Use faster but slightly less accurate settings
        """
        self.device = device if device else check_device()
        self.fast_mode = fast_mode
        self.temp_dir = None

        print(f"✓ Initialized SliceOrganDetector")
        print(f"  Device: {self.device}")
        print(f"  Fast mode: {self.fast_mode}")

    def _prepare_volume_for_totalseg(self, images):
        """
        Convert list of 2D slices into a 3D volume for TotalSegmentator.
        TotalSegmentator expects 3D input (even for slice-level detection).

        Args:
            images (list): List of 2D numpy arrays

        Returns:
            sitk.Image: 3D SimpleITK image
        """
        # Stack slices into 3D volume
        volume = np.stack(images, axis=-1)  # Shape: (H, W, num_slices)

        # Convert to SimpleITK format
        sitk_img = sitk.GetImageFromArray(np.transpose(volume, (2, 0, 1)))  # (Z, H, W)
        sitk_img.SetSpacing([1.0, 1.0, 1.0])  # Dummy spacing

        return sitk_img

    def detect_organs_in_slices(self, images, filenames=None):
        """
        Detect organs present in each slice and return detailed results.

        This is the main inference function. It processes all slices together
        using TotalSegmentator 3D segmentation, then extracts per-slice information.

        Args:
            images (list): List of 2D numpy arrays (one per slice)
            filenames (list): List of filenames corresponding to each slice

        Returns:
            list: List of dicts, one per slice, containing:
                  - filename: slice filename
                  - organs: list of organ names detected
                  - masks: dict mapping organ names to binary masks
                  - confidence: placeholder for confidence scores
        """
        if filenames is None:
            filenames = [f"slice_{i:04d}.dcm" for i in range(len(images))]

        num_slices = len(images)
        print(f"\n{'=' * 70}")
        print(f"Processing {num_slices} slices...")

        # Check VRAM requirements
        vram_needed = estimate_vram_needed(num_slices)
        if self.device.type == 'cuda':
            vram_available = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
            print(f"Estimated VRAM needed: {vram_needed:.1f} GB")
            print(f"Available VRAM: {vram_available:.1f} GB")

            if vram_needed > vram_available * 0.8:
                print("⚠️  Warning: May exceed VRAM. Consider processing fewer slices at once.")

        # Create temporary directory for TotalSegmentator I/O
        self.temp_dir = tempfile.mkdtemp()
        input_path = Path(self.temp_dir) / "input.nii.gz"
        output_path = Path(self.temp_dir) / "output"

        try:
            # Prepare 3D volume from slices
            print("  → Preparing volume for segmentation...")
            sitk_volume = self._prepare_volume_for_totalseg(images)
            sitk.WriteImage(sitk_volume, str(input_path))

            # Run TotalSegmentator
            # Use 'fast' task for speed, 'total' for full segmentation
            task = "fast" if self.fast_mode else "total"
            print(f"  → Running TotalSegmentator (task={task})...")
            print(f"    This may take 30-60 seconds on GPU, 5-10 minutes on CPU...")

            totalsegmentator(
                input=str(input_path),
                output=str(output_path),
                task=task,
                ml=True,  # Use multi-label output (faster)
                nr_thr_resamp=1,
                nr_thr_saving=1,
                fast=self.fast_mode,
                device=self.device.type,
                quiet=False
            )

            # Load segmentation results
            print("  → Loading segmentation masks...")
            seg_files = list(output_path.glob("*.nii.gz"))

            if not seg_files:
                print("⚠️  No segmentation output found. Check TotalSegmentator installation.")
                return []

            # For multi-label output, there's usually one file with all organs
            seg_volume = sitk.ReadImage(str(seg_files[0]))
            seg_array = sitk.GetArrayFromImage(seg_volume)  # Shape: (Z, H, W)

            # Extract per-slice results
            results = []
            for slice_idx in range(num_slices):
                slice_seg = seg_array[slice_idx]  # 2D mask for this slice

                # Find unique organ labels present in this slice
                unique_labels = np.unique(slice_seg)
                unique_labels = unique_labels[unique_labels > 0]  # Exclude background

                # Map labels to organ names
                organs_detected = []
                masks_dict = {}

                for label in unique_labels:
                    organ_name = ORGAN_LABELS.get(int(label), f"structure_{int(label)}")
                    organs_detected.append(organ_name)

                    # Extract binary mask for this organ in this slice
                    organ_mask = (slice_seg == label).astype(np.uint8)
                    masks_dict[organ_name] = organ_mask

                # Calculate pseudo-confidence based on mask size (larger = more confident)
                # Real TotalSegmentator doesn't provide confidence, so we estimate
                confidence = len(unique_labels) / 10.0 if unique_labels.size > 0 else 0.0
                confidence = min(confidence, 1.0)

                result = {
                    'filename': filenames[slice_idx],
                    'slice_index': slice_idx,
                    'organs': organs_detected,
                    'num_organs': len(organs_detected),
                    'masks': masks_dict,
                    'confidence': round(confidence, 3)
                }
                results.append(result)

                # Print progress
                if len(organs_detected) > 0:
                    print(f"    Slice {slice_idx + 1}/{num_slices}: Found {len(organs_detected)} organ(s)")

            print(f"✓ Completed segmentation")
            print(f"{'=' * 70}\n")

            return results

        except Exception as e:
            print(f"✗ Error during segmentation: {e}")
            import traceback
            traceback.print_exc()
            return []

        finally:
            # Clean up temporary directory
            if self.temp_dir and Path(self.temp_dir).exists():
                shutil.rmtree(self.temp_dir)

    def detect_single_slice(self, image, filename="slice.dcm"):
        """
        Convenience method to detect organs in a single slice.

        Args:
            image (np.ndarray): 2D image array
            filename (str): Filename for this slice

        Returns:
            dict: Detection result for this slice
        """
        results = self.detect_organs_in_slices([image], [filename])
        return results[0] if results else None


def main():
    """
    Main function for command-line usage.
    Supports both single file and folder processing.
    """
    parser = argparse.ArgumentParser(
        description="Slice-level organ detection using TotalSegmentator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single DICOM file
  python inference.py --input slice001.dcm --output results/

  # Process folder of DICOM slices
  python inference.py --input dicom_folder/ --output results/

  # Use CPU (slower)
  python inference.py --input slice001.dcm --output results/ --device cpu

  # Fast mode (less accurate but faster)
  python inference.py --input dicom_folder/ --output results/ --fast
        """
    )

    parser.add_argument('--input', '-i', required=True,
                        help='Input DICOM file or folder containing DICOM slices')
    parser.add_argument('--output', '-o', default='results',
                        help='Output directory for results (default: results/)')
    parser.add_argument('--device', choices=['cuda', 'cpu'], default=None,
                        help='Device to use (auto-detected if not specified)')
    parser.add_argument('--fast', action='store_true',
                        help='Use fast mode (less accurate but faster)')
    parser.add_argument('--save-masks', action='store_true',
                        help='Save individual mask images')

    args = parser.parse_args()

    # Determine device
    if args.device:
        device = torch.device(args.device)
    else:
        device = check_device()

    # Initialize detector
    detector = SliceOrganDetector(device=device, fast_mode=args.fast)

    # Load input
    input_path = Path(args.input)
    if input_path.is_file():
        print(f"Loading single DICOM file: {input_path}")
        image, metadata = load_dicom_slice(str(input_path))
        if image is None:
            print("✗ Failed to load DICOM file")
            return
        images = [image]
        filenames = [input_path.name]
    elif input_path.is_dir():
        print(f"Loading DICOM folder: {input_path}")
        images, filenames, metadata_list = load_dicom_folder(str(input_path))
        if not images:
            print("✗ No DICOM files found in folder")
            return
    else:
        print(f"✗ Input path does not exist: {input_path}")
        return

    # Run detection
    results = detector.detect_organs_in_slices(images, filenames)

    if not results:
        print("✗ No results obtained")
        return

    # Prepare results for saving
    results_data = []
    masks_to_save = []

    for result in results:
        for organ in result['organs']:
            results_data.append({
                'filename': result['filename'],
                'slice_index': result['slice_index'],
                'organ': organ,
                'confidence': result['confidence'],
                'mask_path': f"masks/{Path(result['filename']).stem}_{organ}_mask.png" if args.save_masks else ""
            })

            if args.save_masks:
                masks_to_save.append({
                    'filename': f"{Path(result['filename']).stem}_{organ}",
                    'mask': result['masks'][organ]
                })

    # Save results
    csv_path, masks_dir = save_results(
        args.output,
        results_data,
        masks=masks_to_save if args.save_masks else None
    )

    # Print summary
    print(f"\n{'=' * 70}")
    print(f"SUMMARY")
    print(f"{'=' * 70}")
    print(f"Processed slices: {len(results)}")
    print(f"Total organs detected: {len(results_data)}")
    print(f"Results saved to: {csv_path}")
    if masks_dir:
        print(f"Masks saved to: {masks_dir}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()