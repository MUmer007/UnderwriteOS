import os
from typing import Any

import pdfplumber
import pymupdf

from uw.llm.client import call_structured
from uw.llm.schemas import StatementOut


def extract_from_pdf(pdf_path: str, text_model: str, vision_model: str) -> dict[str, Any]:
    text_content = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_content += text + "\n"

    if len(text_content.strip()) > 150:
        print(f"  -> Routing {os.path.basename(pdf_path)} to TEXT model")
        system_prompt = "You are an expert financial document extractor. Extract all transactions and balances accurately. Return ONLY valid JSON."

        result, usage, latency = call_structured(
            model=text_model,
            system_prompt=system_prompt,
            user_text=f"Extract data from this bank statement text:\n\n{text_content}",
            schema=StatementOut,
        )
        return {"result": result, "usage": usage, "latency": latency, "path": "text"}
    else:
        print(f"  -> Routing {os.path.basename(pdf_path)} to VISION model (low text)")
        doc = pymupdf.open(pdf_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=150)
            images.append(pix.tobytes("png"))
        doc.close()

        system_prompt = "You are an expert financial document extractor. Read the bank statement from the provided image(s). Extract all transactions and balances accurately. Return ONLY valid JSON."

        result, usage, latency = call_structured(
            model=vision_model,
            system_prompt=system_prompt,
            user_text="Extract data from these bank statement pages.",
            schema=StatementOut,
            images=images[:3],
        )
        return {"result": result, "usage": usage, "latency": latency, "path": "vision"}
