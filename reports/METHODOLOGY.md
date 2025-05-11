# Methodology for Nuclei/Mitosis Counting:

Basic analysis on starting point for both usage and training and what we get or have as datasets.

## **1. Dataset Structure**
- **Bare images**: High-resolution Ki-67 stained tissue images.
- **256x256 patches**: Preprocessed sub-regions for training.
- **512x512 patches**: Preprocessed sub-regions for training.
- **JSON files**: Annotations with coordinates and nuclei counts.
- **Labeled images**: Ki-67 marked images.
  
## **2. Key Steps**

### **2.1. Preprocessing (for usage)**
- **Stain normalization**: Apply `Macenko/Vahadane` to align color spaces between training datatset and desired hospital images.
- **Mask generation**: Convert JSON point annotations to binary masks (1 for nuclei, 0 for background).

### **2.2. Data Augmentation (for training)**
Since the dataset is small, augmenting images is crucial. Basic methods like rotations, flips, and color changes are standard. But maybe they can use more advanced techniques like generative models. GANs or diffusion models could generate synthetic data. Also, mixing images with CutMix or Mosaic might help. They should also check if the dataset is class-balanced; if not, maybe oversample rare classes.
