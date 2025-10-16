"""
Complete MPR Organ Detection System with DICOM Conversion
- Uses TotalSegmentator AI model for accurate organ detection
- Converts any medical image format TO DICOM
- User selects file via GUI
- Shows organ names and details
"""

import os
import numpy as np
import nibabel as nib
from totalsegmentator.python_api import totalsegmentator
import json
from pathlib import Path
from tkinter import Tk, filedialog, messagebox
import shutil
from datetime import datetime
import SimpleITK as sitk
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.uid import generate_uid
import time


class OrganDetectorWithDICOM:
    """
    Complete organ detection system with DICOM conversion
    """

    def __init__(self):
        """Initialize with organ name mappings"""

        # Complete organ name mapping from TotalSegmentator
        self.organ_names = {
            1: 'Spleen', 2: 'Kidney Right', 3: 'Kidney Left', 4: 'Gallbladder',
            5: 'Liver', 6: 'Stomach', 7: 'Pancreas', 8: 'Adrenal Gland Right',
            9: 'Adrenal Gland Left', 10: 'Lung Upper Lobe Left', 11: 'Lung Lower Lobe Left',
            12: 'Lung Upper Lobe Right', 13: 'Lung Middle Lobe Right', 14: 'Lung Lower Lobe Right',
            15: 'Esophagus', 16: 'Trachea', 17: 'Thyroid Gland', 18: 'Small Bowel',
            19: 'Duodenum', 20: 'Colon', 21: 'Urinary Bladder', 22: 'Prostate',
            23: 'Kidney Cyst Left', 24: 'Kidney Cyst Right', 55: 'Heart', 56: 'Aorta',
            57: 'Pulmonary Vein', 58: 'Brachiocephalic Trunk', 59: 'Subclavian Artery Right',
            60: 'Subclavian Artery Left', 61: 'Common Carotid Artery Right',
            62: 'Common Carotid Artery Left', 63: 'Brachiocephalic Vein Left',
            64: 'Brachiocephalic Vein Right', 65: 'Atrial Appendage Left',
            66: 'Superior Vena Cava', 67: 'Inferior Vena Cava',
            68: 'Portal Vein and Splenic Vein', 69: 'Iliac Artery Left',
            70: 'Iliac Artery Right', 71: 'Iliac Vena Left', 72: 'Iliac Vena Right',
            103: 'Brain', 104: 'Skull', 105: 'Rib Left', 106: 'Rib Right',
            107: 'Vertebrae', 108: 'Spinal Cord'
        }

        self.temp_dir = None

    def browse_file(self):
        """Open file browser to select input file"""
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)

        print("\n" + "="*70)
        print("📂 SELECT YOUR MEDICAL IMAGE FILE")
        print("="*70)
        print("Supported: DICOM (.dcm), NIfTI (.nii, .nii.gz), MHD (.mhd)")

        file_path = filedialog.askopenfilename(
            title="Select Medical Image",
            filetypes=[
                ("All Medical", "*.dcm *.nii *.nii.gz *.mhd *.mha"),
                ("DICOM", "*.dcm"),
                ("NIfTI", "*.nii *.nii.gz"),
                ("MHD/MHA", "*.mhd *.mha"),
                ("All files", "*.*")
            ]
        )

        root.destroy()

        if file_path:
            print(f"\n✅ File selected: {os.path.basename(file_path)}")
            print(f"📍 Path: {file_path}")
            return file_path
        else:
            print("\n❌ No file selected")
            return None

    def convert_to_nifti(self, input_path):
        """
        Convert any format to NIfTI (for TotalSegmentator)

        Args:
            input_path: Path to input file

        Returns:
            str: Path to NIfTI file
        """
        ext = os.path.splitext(input_path)[1].lower()

        print("\n" + "="*70)
        print("🔄 PREPARING FILE FOR PROCESSING")
        print("="*70)

        # If already NIfTI, return as is
        if ext in ['.nii', '.gz']:
            print("✅ File is already NIfTI format")
            return input_path

        # Create temp directory
        input_dir = os.path.dirname(input_path)
        self.temp_dir = os.path.join(input_dir, 'temp_processing')
        os.makedirs(self.temp_dir, exist_ok=True)

        output_nifti = os.path.join(self.temp_dir, 'temp_for_segmentation.nii.gz')

        print(f"📄 Converting {ext.upper()} to NIfTI...")

        try:
            if ext in ['.mhd', '.mha']:
                img = sitk.ReadImage(input_path)
                sitk.WriteImage(img, output_nifti)

            elif ext == '.dcm':
                # Check if it's a single file or series
                parent_dir = os.path.dirname(input_path)
                dcm_files = list(Path(parent_dir).glob('*.dcm'))

                if len(dcm_files) > 1:
                    print(f"   Found {len(dcm_files)} DICOM files - loading as series")
                    reader = sitk.ImageSeriesReader()
                    dicom_names = reader.GetGDCMSeriesFileNames(parent_dir)
                    reader.SetFileNames(dicom_names)
                    img = reader.Execute()
                else:
                    print("   Loading single DICOM file")
                    img = sitk.ReadImage(input_path)

                sitk.WriteImage(img, output_nifti)

            else:
                # Try generic conversion
                img = sitk.ReadImage(input_path)
                sitk.WriteImage(img, output_nifti)

            print(f"✅ Converted to NIfTI: {output_nifti}")
            return output_nifti

        except Exception as e:
            print(f"❌ Conversion error: {str(e)}")
            raise

    def convert_to_dicom(self, nifti_path, output_dir):
        """
        Convert NIfTI to DICOM format

        Args:
            nifti_path: Path to NIfTI file
            output_dir: Directory to save DICOM files

        Returns:
            str: Path to DICOM output directory
        """
        print("\n" + "="*70)
        print("🔄 CONVERTING TO DICOM FORMAT")
        print("="*70)

        dicom_output_dir = os.path.join(output_dir, 'dicom_output')
        os.makedirs(dicom_output_dir, exist_ok=True)

        try:
            # Read NIfTI
            print("📖 Reading NIfTI file...")
            nifti_img = nib.load(nifti_path)
            nifti_data = nifti_img.get_fdata()

            # Get image properties
            shape = nifti_data.shape
            spacing = nifti_img.header.get_zooms()

            print(f"   Image shape: {shape}")
            print(f"   Voxel spacing: {spacing}")

            # Normalize data to proper range
            data_min = nifti_data.min()
            data_max = nifti_data.max()

            if data_max > data_min:
                normalized_data = ((nifti_data - data_min) / (data_max - data_min) * 4095).astype(np.uint16)
            else:
                normalized_data = nifti_data.astype(np.uint16)

            print(f"\n💾 Creating DICOM series ({shape[2]} slices)...")

            # Create DICOM series
            series_uid = generate_uid()
            study_uid = generate_uid()

            for i in range(shape[2]):
                # Create new DICOM dataset
                file_meta = Dataset()
                file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.2'  # CT Image Storage
                file_meta.MediaStorageSOPInstanceUID = generate_uid()
                file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'  # Implicit VR Little Endian
                file_meta.ImplementationClassUID = generate_uid()

                ds = FileDataset(
                    filename=f"slice_{i:04d}.dcm",
                    dataset=Dataset(),
                    file_meta=file_meta,
                    preamble=b"\0" * 128
                )

                # Set required DICOM tags
                ds.PatientName = "Anonymous"
                ds.PatientID = "000000"
                ds.PatientBirthDate = "19000101"
                ds.PatientSex = "O"

                ds.StudyInstanceUID = study_uid
                ds.SeriesInstanceUID = series_uid
                ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
                ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

                ds.Modality = "CT"
                ds.StudyDate = datetime.now().strftime("%Y%m%d")
                ds.StudyTime = datetime.now().strftime("%H%M%S")
                ds.SeriesDate = datetime.now().strftime("%Y%m%d")
                ds.SeriesTime = datetime.now().strftime("%H%M%S")
                ds.ContentDate = datetime.now().strftime("%Y%m%d")
                ds.ContentTime = datetime.now().strftime("%H%M%S")

                ds.StudyDescription = "Converted from NIfTI"
                ds.SeriesDescription = "Organ Detection Study"
                ds.SeriesNumber = 1
                ds.InstanceNumber = i + 1

                # Image data
                ds.SamplesPerPixel = 1
                ds.PhotometricInterpretation = "MONOCHROME2"
                ds.Rows = shape[0]
                ds.Columns = shape[1]
                ds.BitsAllocated = 16
                ds.BitsStored = 12
                ds.HighBit = 11
                ds.PixelRepresentation = 0

                ds.PixelSpacing = [float(spacing[0]), float(spacing[1])]
                ds.SliceThickness = float(spacing[2])
                ds.ImagePositionPatient = [0, 0, float(i * spacing[2])]
                ds.ImageOrientationPatient = [1, 0, 0, 0, 1, 0]

                # Pixel data
                slice_data = normalized_data[:, :, i]
                ds.PixelData = slice_data.tobytes()

                # Save DICOM file
                output_filename = os.path.join(dicom_output_dir, f"slice_{i:04d}.dcm")
                ds.save_as(output_filename, write_like_original=False)

                # Progress indicator
                if (i + 1) % 10 == 0 or i == shape[2] - 1:
                    progress = ((i + 1) / shape[2]) * 100
                    print(f"   Progress: {progress:.1f}% ({i + 1}/{shape[2]} slices)", end='\r')

            print(f"\n✅ DICOM conversion completed!")
            print(f"📁 DICOM files saved to: {dicom_output_dir}")
            print(f"📊 Total slices created: {shape[2]}")

            return dicom_output_dir

        except Exception as e:
            print(f"\n❌ DICOM conversion error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def run_totalsegmentator(self, nifti_path, output_dir):
        """
        Run TotalSegmentator for organ detection

        Args:
            nifti_path: Path to NIfTI file
            output_dir: Output directory

        Returns:
            dict: Detection results
        """
        print("\n" + "="*70)
        print("🧠 RUNNING TOTALSEGMENTATOR AI MODEL")
        print("="*70)
        print("⏳ This will take 2-5 minutes - please be patient...")
        print("☕ Grab a coffee while the AI works!\n")

        seg_output_dir = os.path.join(output_dir, 'segmentation_results')
        os.makedirs(seg_output_dir, exist_ok=True)

        start_time = time.time()

        try:
            # Run TotalSegmentator
            totalsegmentator(
                input=nifti_path,
                output=seg_output_dir,
                fast=True,  # Fast mode for quicker results
                ml=True
            )

            elapsed_time = time.time() - start_time
            print(f"\n✅ Segmentation completed in {elapsed_time:.1f} seconds!")

            # Analyze results
            organs = self._analyze_segmentation(seg_output_dir)

            return {
                'segmentation_dir': seg_output_dir,
                'organs': organs,
                'processing_time': elapsed_time
            }

        except Exception as e:
            print(f"\n❌ Segmentation error: {str(e)}")
            raise

    def _analyze_segmentation(self, seg_dir):
        """Analyze segmentation results and extract organ info"""
        print("\n📊 Analyzing detected organs...")

        detected_organs = []
        seg_file = Path(seg_dir) / 'segmentations.nii.gz'

        if not seg_file.exists():
            print("⚠️  No segmentation file found")
            return detected_organs

        try:
            seg_img = nib.load(str(seg_file))
            seg_data = seg_img.get_fdata()

            unique_labels = np.unique(seg_data)
            unique_labels = unique_labels[unique_labels > 0]

            print(f"✅ Found {len(unique_labels)} organs:\n")

            for label in unique_labels:
                label_id = int(label)
                organ_name = self.organ_names.get(label_id, f'Unknown_{label_id}')

                organ_mask = (seg_data == label)
                volume_voxels = np.sum(organ_mask)

                if volume_voxels > 0:
                    voxel_dims = seg_img.header.get_zooms()
                    volume_mm3 = volume_voxels * np.prod(voxel_dims)

                    organ_info = {
                        'name': organ_name,
                        'label_id': label_id,
                        'volume_voxels': int(volume_voxels),
                        'volume_mm3': float(volume_mm3),
                        'volume_ml': float(volume_mm3 / 1000)
                    }

                    detected_organs.append(organ_info)
                    print(f"   ✓ {organ_name}")

            detected_organs.sort(key=lambda x: x['volume_mm3'], reverse=True)

        except Exception as e:
            print(f"❌ Analysis error: {str(e)}")

        return detected_organs

    def print_results(self, results):
        """Print detailed results"""
        print("\n\n" + "="*70)
        print("🎯 ORGAN DETECTION RESULTS")
        print("="*70)

        print(f"\n📁 Input: {os.path.basename(results['input_file'])}")
        print(f"📅 Date: {results['timestamp']}")
        print(f"⏱️  Processing time: {results['processing_time']:.1f} seconds")
        print(f"🔢 Total organs: {len(results['organs'])}")

        if results['organs']:
            print("\n" + "="*70)
            print("📋 DETECTED ORGANS (sorted by volume)")
            print("="*70)

            for idx, organ in enumerate(results['organs'], 1):
                print(f"\n{idx}. 🫀 {organ['name'].upper()}")
                print(f"   {'─'*60}")
                print(f"   Label ID: {organ['label_id']}")
                print(f"   Volume: {organ['volume_mm3']:.2f} mm³ ({organ['volume_ml']:.2f} mL)")
        else:
            print("\n⚠️  No organs detected")

        print("\n" + "="*70)
        print("📁 OUTPUT FILES:")
        print("="*70)
        print(f"   • Segmentation: {results['segmentation_dir']}")
        if results.get('dicom_dir'):
            print(f"   • DICOM output: {results['dicom_dir']}")
        print("="*70)

    def cleanup(self):
        """Clean temporary files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print("\n🧹 Temporary files cleaned")
            except:
                pass

    def run(self):
        """Main execution"""
        print("\n🏥 " + "="*66 + " 🏥")
        print("🏥" + " "*10 + "ORGAN DETECTION + DICOM CONVERTER" + " "*20 + "🏥")
        print("🏥 " + "="*66 + " 🏥")
        print("\n✨ Features:")
        print("   • AI-powered organ detection (TotalSegmentator)")
        print("   • Converts any format TO DICOM")
        print("   • Detailed organ analysis")

        input("\n👉 Press ENTER to start...")

        try:
            # Select file
            input_file = self.browse_file()
            if not input_file:
                return None

            # Convert to NIfTI for processing
            nifti_file = self.convert_to_nifti(input_file)

            # Create output directory
            output_dir = os.path.join(
                os.path.dirname(input_file),
                f'organ_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            )
            os.makedirs(output_dir, exist_ok=True)

            # Run organ detection
            seg_results = self.run_totalsegmentator(nifti_file, output_dir)

            # Convert to DICOM
            dicom_dir = self.convert_to_dicom(nifti_file, output_dir)

            # Prepare final results
            results = {
                'input_file': input_file,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'processing_time': seg_results['processing_time'],
                'organs': seg_results['organs'],
                'segmentation_dir': seg_results['segmentation_dir'],
                'dicom_dir': dicom_dir
            }

            # Save JSON
            json_file = os.path.join(output_dir, 'results.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4, ensure_ascii=False)

            # Print results
            self.print_results(results)

            # Show popup
            root = Tk()
            root.withdraw()
            messagebox.showinfo(
                "✅ Complete!",
                f"Detected {len(results['organs'])} organs!\n\n"
                f"DICOM files created: {dicom_dir}\n\n"
                f"Check console for details."
            )
            root.destroy()

            self.cleanup()
            return results

        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

            root = Tk()
            root.withdraw()
            messagebox.showerror("Error", str(e))
            root.destroy()

            self.cleanup()
            return None


def main():
    """Entry point"""
    detector = OrganDetectorWithDICOM()
    results = detector.run()

    if results:
        print(f"\n✅ SUCCESS! Detected {len(results['organs'])} organs")
    else:
        print("\n❌ Process failed or cancelled")

    input("\nPress ENTER to exit...")


if __name__ == "__main__":
    main()