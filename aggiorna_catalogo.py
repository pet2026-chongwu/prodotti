"""Create public catalog files from a product export and optional image archive."""
import argparse
import base64
import csv
import hashlib
import io
import json
import re
import tarfile
import sys
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

RULES = [
    ("Pesca", "Articoli da pesca", r"\b(pesca|esca|esche|ami|amo|lenza|mulinello|piombi|girella|galleggiante)\b"),
    ("Acquariologia", "Accessori per acquario", r"acquar|aerator|termoriscaldat"),
    ("Guinzaglieria", "Collari, guinzagli e pettorine", r"guinzagl|collar|pettorin|museruol"),
    ("Cura e toelettatura", "Spazzole e toelettatura", r"pettin[eia]|spazzol|cardator|tagliaungh|shampoo|balsamo|repellente|attrattivo"),
    ("Igiene per animali", "Accessori per l’igiene", r"lettier|assorbent|igienic|salviett|pannolin|raccogli|sacchett|paletta"),
    ("Giocattoli per animali", "Giochi", r"gioc|pallin|peluche|tiragraff|corda|frisbee"),
    ("Articoli per l'alimentazione", "Ciotole e accessori", r"ciotol|ciottol|dispenser|mangiato|abbever|fontanella"),
    ("Alimenti per animali", "Cibo e snack", r"mangime|crocchett|snack|natural mix|naturalmix|pat[eéè]|filetti"),
    ("Cucce e tappetini", "Cucce e cuscini", r"cucc|cuscin|tappet|materassin|copert"),
    ("Abbigliamento per animali", "Vestiti e accessori", r"maglion|impermeabil|cappott|abbigliamento|vestit|felpa|giubbot"),
    ("Articoli da passeggio", "Trasporto", r"trasportin|borsa|zain|passeggin"),
    ("Gabbie per animali", "Gabbie e accessori", r"gabbi|volier"),
]


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def image_bundles(archive, codes):
    with tarfile.open(archive, "r:*") as source:
        bundle, length = {}, 0
        for item in source:
            path = Path(item.name)
            code = path.stem
            if not item.isfile() or item.size > 20_000_000 or code not in codes:
                continue
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            try:
                with source.extractfile(item) as stream, Image.open(io.BytesIO(stream.read())) as original:
                    image = ImageOps.exif_transpose(original).convert("RGB")
                    image.thumbnail((220, 220), Image.Resampling.LANCZOS)
                    output = io.BytesIO()
                    image.save(output, "WEBP", quality=65)
            except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
                print(f"图片跳过 {item.name}: {error}")
                continue
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
            if bundle and length + len(encoded) > 68_000:
                yield bundle
                bundle, length = {}, 0
            bundle[code] = encoded
            length += len(encoded) + len(code) + 8
        if bundle:
            yield bundle


def select_exports():
    import tkinter as tk
    from tkinter import filedialog

    window = tk.Tk()
    window.withdraw()
    try:
        csv_path = filedialog.askopenfilename(title="选择商品 CSV", filetypes=[("CSV", "*.csv")])
        if not csv_path:
            return []
        images = filedialog.askopenfilename(
            title="选择图片压缩包（没有新图可取消）",
            filetypes=[("TAR / TAR.GZ", "*.tar *.tar.gz *.tgz")],
        )
        return [csv_path, images] if images else [csv_path]
    finally:
        window.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("images", nargs="?", type=Path)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    arguments = sys.argv[1:] or select_exports()
    if not arguments:
        return
    args = parser.parse_args(arguments)
    folder = args.root / "catalogo"
    photos = folder / "foto"
    photos.mkdir(parents=True, exist_ok=True)
    previous = read_json(folder / "prodotti.json", [])
    old = {p["code"]: (p["main_cat"], p["sub_cat"], p["name"]) for p in previous}
    references = {p["code"]: p["photo"] for p in previous if p.get("photo")}
    overrides = read_json(folder / "categorie.json", {})
    products = {}
    with args.csv.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        required = {"product_model", "local_description", "product_barcode", "inner_quantity", "unit_quantity"}
        if not required.issubset(rows.fieldnames or []):
            parser.error("CSV 缺少商品型号、意大利语名称、条码或装箱字段")
        for row in rows:
            code = row["product_model"].strip()
            if not code or code in products:
                parser.error(f"商品型号为空或重复，CSV 第 {rows.line_num} 行")
            prior = old.get(code, ("", "", ""))
            name = row["local_description"].strip() or prior[2] or code
            if code in overrides:
                category, subcategory = overrides[code]
            elif prior[0] and prior[0] not in {"Non categorizzato", "Altri articoli"}:
                category, subcategory = prior[:2]
            else:
                category, subcategory = next(
                    ((cat, sub) for cat, sub, pattern in RULES if re.search(pattern, name, re.I)),
                    ("Altri articoli", "Altro"),
                )
            products[code] = dict(code=code, name=name, barcode=row["product_barcode"].strip(),
                                  main_cat=category, sub_cat=subcategory,
                                  pack=row["inner_quantity"].strip(), box=row["unit_quantity"].strip())
    if not products:
        parser.error("CSV 没有商品")
    if args.images:
        for bundle in image_bundles(args.images, products):
            payload = json.dumps(bundle, separators=(",", ":"))
            filename = hashlib.sha256(payload.encode()).hexdigest()[:20] + ".json"
            write_json(photos / filename, bundle)
            references.update(dict.fromkeys(bundle, "foto/" + filename))
    for code, product in products.items():
        product["photo"] = references.get(code, "")
    write_json(folder / "prodotti.json", list(products.values()))
    used = {p["photo"] for p in products.values()}
    for file in photos.glob("*.json"):
        if re.fullmatch(r"[0-9a-f]{20}\.json", file.name) and "foto/" + file.name not in used:
            file.unlink()
    print(f"{len(products)} 个商品，{sum(bool(p['photo']) for p in products.values())} 个有图")


if __name__ == "__main__":
    main()
