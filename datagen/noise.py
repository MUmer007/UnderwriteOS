import os
import random
import pymupdf
import cv2
import numpy as np
from PIL import Image
import io

def apply_noise(input_pdf: str, output_pdf: str):
    doc = pymupdf.open(input_pdf)
    new_doc = pymupdf.open()
    
    for page in doc:
        # Rasterize at ~150 DPI
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        
        # Convert to OpenCV format (numpy array)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 1. Rotation (+- 2 degrees)
        angle = random.uniform(-2, 2)
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
        img = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))
        
        # 2. Gaussian Blur
        if random.random() > 0.5:
            img = cv2.GaussianBlur(img, (3, 3), 0)
            
        # 3. Salt and Pepper noise
        if random.random() > 0.5:
            row, col, ch = img.shape
            s_vs_p = 0.5
            amount = 0.004
            num_salt = int(amount * img.size * s_vs_p)
            coords = [np.random.randint(0, i - 1, num_salt) for i in img.shape]
            img[coords] = 255
            num_pepper = int(amount * img.size * (1. - s_vs_p))
            coords = [np.random.randint(0, i - 1, num_pepper) for i in img.shape]
            img[coords] = 0
            
        # Convert back to PIL for JPEG compression artifacting
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        buffer = io.BytesIO()
        quality = random.randint(40, 80)
        img_pil.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        
        # Insert rasterized image as a full page in new PDF (strips text layer)
        img_rect = pymupdf.Rect(0, 0, page.rect.width, page.rect.height)
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(img_rect, stream=buffer.getvalue())
        
    # FIX: Save to a temporary file first to avoid Windows file lock issues
    temp_pdf = input_pdf + ".tmp"
    new_doc.save(temp_pdf)
    
    # Close documents BEFORE replacing the original file
    new_doc.close()
    doc.close()
    
    # Atomically replace the original file with the noisy version
    os.replace(temp_pdf, output_pdf)

def apply_noise_to_folder(folder_path: str):
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            if random.random() < 0.5: # Apply noise to 50% of documents
                filepath = os.path.join(folder_path, filename)
                print(f"Applying noise to {filepath}")
                apply_noise(filepath, filepath)

if __name__ == "__main__":
    # Clean up any leftover .tmp files from the previous crash
    for folder in ["data/synthetic/clean", "data/synthetic/tampered"]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".tmp"):
                    os.remove(os.path.join(folder, f))

    apply_noise_to_folder("data/synthetic/clean")
    apply_noise_to_folder("data/synthetic/tampered")
    print("✅ Noise applied to 50% of clean and tampered statements.")