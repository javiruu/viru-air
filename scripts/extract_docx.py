"""Extrae texto de documentos .docx de la carpeta fases."""

import glob
import os
import zipfile
from xml.etree import ElementTree as ET

BASE = os.path.join(os.path.dirname(__file__), "..", "fases")
OUT = os.path.join(BASE, "_extraido_txt")
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_docx(path: str) -> str:
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ET.fromstring(xml)
    lines: list[str] = []
    for p in root.findall(".//w:p", NS):
        text = "".join(t.text for t in p.findall(".//w:t", NS) if t.text)
        text = text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for path in glob.glob(os.path.join(BASE, "*.docx")):
        name = os.path.splitext(os.path.basename(path))[0]
        out = os.path.join(OUT, f"{name}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(extract_docx(path))
        print(f"extraido: {out}")


if __name__ == "__main__":
    main()
