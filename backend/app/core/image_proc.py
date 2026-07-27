import cv2
import numpy as np
from pathlib import Path

def load_image(image_path: Path) -> np.ndarray:
    """Loads an image from the disk. Raises FileNotFoundError or ValueError if invalid."""
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Failed to load image file. It may be corrupted: {image_path}")
    
    return image

def resize_image(image: np.ndarray, max_dim: int = 1800) -> np.ndarray:
    """Resizes the image proportionally if either dimension exceeds max_dim."""
    h, w = image.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return image

def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Converts a BGR image to grayscale."""
    if len(image.shape) == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image.copy()

def remove_noise(image: np.ndarray) -> np.ndarray:
    """Applies noise reduction filter."""
    return cv2.GaussianBlur(image, (3, 3), 0)

def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Applies CLAHE to normalize scan illumination variations."""
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

def deskew(image: np.ndarray) -> np.ndarray:
    """Automatically corrects rotation tilts in scanned pages."""
    gray = to_grayscale(image)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    lines = cv2.HoughLinesP(
        thresh, 
        rho=1, 
        theta=np.pi / 180, 
        threshold=100, 
        minLineLength=100, 
        maxLineGap=10
    )
    
    if lines is None:
        return image
        
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -45 < angle < 45:
            angles.append(angle)
        elif angle > 135:
            angles.append(angle - 180)
        elif angle < -135:
            angles.append(angle + 180)
            
    if not angles:
        return image
        
    median_angle = np.median(angles)
    if abs(median_angle) < 0.1:
        return image
        
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    
    return cv2.warpAffine(
        image, 
        M, 
        (w, h), 
        flags=cv2.INTER_CUBIC, 
        borderMode=cv2.BORDER_REPLICATE
    )

def threshold(image: np.ndarray) -> np.ndarray:
    """Binarizes the grayscale image using Otsu's adaptive binarization."""
    gray = to_grayscale(image)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary

def morphological_clean(image: np.ndarray) -> np.ndarray:
    """Welds text segments using morphological operations."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)

def preprocess_image_pipeline(image_path: Path, save_verification_path: Path = None) -> np.ndarray:
    """Runs the complete image cleaning pipeline and saves the binarized image."""
    img = load_image(image_path)
    img = resize_image(img, max_dim=3000)
    img = deskew(img)
    gray = to_grayscale(img)
    cleaned = remove_noise(gray)
    
    if save_verification_path is not None:
        save_verification_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(save_verification_path), cleaned)
        
    return cleaned
