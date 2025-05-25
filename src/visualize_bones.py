import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from pathlib import Path
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.animation import FuncAnimation
import SimpleITK as sitk

def create_orthogonal_views(image_data, output_path, title="CT Scan with Bone Segmentation"):
    """
    Create orthogonal views (axial, sagittal, coronal) of the image
    """
    # Get the middle slices for each view
    z_mid = image_data.shape[0] // 2
    y_mid = image_data.shape[1] // 2
    x_mid = image_data.shape[2] // 2
    
    # Create the figure
    fig, axes = plt.subplots(2, 2, figsize=(12, 12))
    fig.suptitle(title, fontsize=16)
    
    # Plot axial view (top-down)
    axes[0, 0].imshow(image_data[z_mid, :, :], cmap='bone')
    axes[0, 0].set_title('Axial View')
    axes[0, 0].axis('off')
    
    # Plot sagittal view (side)
    axes[0, 1].imshow(image_data[:, y_mid, :], cmap='bone')
    axes[0, 1].set_title('Sagittal View')
    axes[0, 1].axis('off')
    
    # Plot coronal view (front)
    axes[1, 0].imshow(image_data[:, :, x_mid], cmap='bone')
    axes[1, 0].set_title('Coronal View')
    axes[1, 0].axis('off')
    
    # Add text in the empty subplot
    axes[1, 1].text(0.5, 0.5, 'Bone Segmentation\nVisualization',
                   ha='center', va='center', fontsize=12)
    axes[1, 1].axis('off')
    
    # Save the figure
    plt.savefig(output_path)
    plt.close()

def create_3d_surface(image_data, output_path, threshold=0.5):
    """
    Create a 3D surface plot of the segmentation
    """
    # Create a figure for 3D visualization
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Get the coordinates of segmented voxels
    x, y, z = np.where(image_data > threshold)
    
    # Create the 3D scatter plot
    scatter = ax.scatter(x, y, z, c=z, cmap='viridis', alpha=0.1, s=1)
    
    # Set labels and title
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('3D Bone Visualization')
    
    # Add a color bar
    plt.colorbar(scatter)
    
    # Save the figure
    plt.savefig(output_path)
    plt.close()

def create_rotating_gif(image_data, output_path, threshold=0.5):
    """
    Create a rotating GIF of the 3D visualization
    """
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Get the coordinates of segmented voxels
    x, y, z = np.where(image_data > threshold)
    
    def update(frame):
        ax.clear()
        ax.scatter(x, y, z, c=z, cmap='viridis', alpha=0.1, s=1)
        ax.view_init(elev=20., azim=frame)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('3D Bone Visualization')
    
    # Create the animation
    anim = FuncAnimation(fig, update, frames=np.arange(0, 360, 2), repeat=True)
    anim.save(output_path, writer='pillow', fps=15)
    plt.close()

def main():
    # Set up directories
    input_dir = Path("data/preprocessed")
    seg_dir = Path("data/bone_segmentation")
    viz_dir = Path("data/bone_segmentation/visualizations")
    viz_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each segmentation file
    for seg_file in seg_dir.glob("*_bone_seg.nii.gz"):
        print(f"Processing {seg_file.name}")
        
        # Load the segmentation
        seg_img = nib.load(str(seg_file))
        seg_data = seg_img.get_fdata()
        
        # Get the corresponding original file
        orig_file = input_dir / seg_file.name.replace("_bone_seg.nii.gz", ".nii.gz")
        if orig_file.exists():
            orig_img = nib.load(str(orig_file))
            orig_data = orig_img.get_fdata()
            
            # Create overlay of original and segmentation
            overlay_data = np.copy(orig_data)
            overlay_data[seg_data > 0] = np.max(orig_data)  # Highlight segmented regions
        else:
            overlay_data = seg_data
        
        # Generate base filename for outputs
        base_name = seg_file.stem.replace(".nii", "")
        
        # Create and save visualizations
        print("Creating orthogonal views...")
        create_orthogonal_views(
            overlay_data,
            viz_dir / f"{base_name}_orthogonal.png"
        )
        
        print("Creating 3D surface plot...")
        create_3d_surface(
            seg_data,
            viz_dir / f"{base_name}_3d_surface.png"
        )
        
        print("Creating rotating GIF...")
        create_rotating_gif(
            seg_data,
            viz_dir / f"{base_name}_rotating.gif"
        )
        
        print(f"Visualizations saved in {viz_dir}")

if __name__ == "__main__":
    main() 