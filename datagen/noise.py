import io
import os
import random

import cv2
import numpy as np
import pymupdf
from PIL import Image


def apply_noise(input_pdf: str, output_pdf: str):
    doc = pymupdf.open(input_pdf)
    new_doc = pymupdf.open()

    for page in doc:
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")

        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        angle = random.uniform(-2, 2)
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
        img = cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))

        if random.random() > 0.5:
            img = cv2.GaussianBlur(img, (3, 3), 0)

        if random.random() > 0.5:
            row, col, ch = img.shape
            s_vs_p = 0.5
            amount = 0.004
            num_salt = int(amount * img.size * s_vs_p)
            coords = [np.random.randint(0, i - 1, num_salt) for i in img.shape]
            img[coords] = 255
            num_pepper = int(amount * img.size * (1.0 - s_vs_p))
            coords = [np.random.randint(0, i - 1, num_pepper) for i in img.shape]
            img[coords] = 0

        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        buffer = io.BytesIO()
        quality = random.randint(40, 80)
        img_pil.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)

        img_rect = pymupdf.Rect(0, 0, page.rect.width, page.rect.height)
        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(img_rect, stream=buffer.getvalue())

    temp_pdf = input_pdf + ".tmp"
    new_doc.save(temp_pdf)

    new_doc.close()
    doc.close()

    os.replace(temp_pdf, output_pdf)


def apply_noise_to_folder(folder_path: str):
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf") and random.random() < 0.5:
            filepath = os.path.join(folder_path, filename)
            print(f"Applying noise to {filepath}")
            apply_noise(filepath, filepath)


if __name__ == "__main__":
    for folder in ["data/synthetic/clean", "data/synthetic/tampered"]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                if f.endswith(".tmp"):
                    os.remove(os.path.join(folder, f))

    apply_noise_to_folder("data/synthetic/clean")
    apply_noise_to_folder("data/synthetic/tampered")
    print("? Noise applied to 50% of clean and tampered statements.")
