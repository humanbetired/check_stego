import os
import sys
import imghdr
import shutil
import struct
import binascii
from pathlib import Path
from PIL import Image, ImageOps, ExifTags
import io

try:
    import magic
    HAVE_MAGIC = True
except:
    HAVE_MAGIC = False

def detect_file_type(path: Path):
    if HAVE_MAGIC:
        try:
            m = magic.from_file(str(path), mime=True)
            if m.startswith("image/png"): return "png"
            if m.startswith("image/jpeg"): return "jpg"
            if m.startswith("image/gif"): return "gif"
            if m.startswith("image/bmp"): return "bmp"
            if m.startswith("image/webp"): return "webp"
        except:
            pass

    kind = imghdr.what(str(path))
    if kind == "jpeg":
        return "jpg"
    return kind


def rename_with_extension(path: Path, ext: str):
    newpath = path.with_suffix("." + ext)
    if path == newpath:
        return path
    i = 1
    cand = newpath
    while cand.exists():
        cand = newpath.with_name(f"{newpath.stem}_{i}{newpath.suffix}")
        i += 1
    path.rename(cand)
    return cand

PNG_SIG = b'\x89PNG\r\n\x1a\n'

def repair_png_crc(path: Path, outpath: Path = None):
    data = path.read_bytes()
    if not data.startswith(PNG_SIG):
        return False, "not_png"

    i = len(PNG_SIG)
    out = bytearray(PNG_SIG)
    changed = False

    while i < len(data):
        if i + 8 > len(data):
            break
        
        length = struct.unpack(">I", data[i:i+4])[0]
        ctype = data[i+4:i+8]
        i += 8

        if i + length + 4 > len(data):
            break

        chunkdata = data[i:i+length]
        i += length
        crc_old = data[i:i+4]
        i += 4

        crc_new = struct.pack(">I", binascii.crc32(ctype + chunkdata) & 0xffffffff)

        out.extend(struct.pack(">I", length))
        out.extend(ctype)
        out.extend(chunkdata)
        out.extend(crc_new)

        if crc_new != crc_old:
            changed = True

        if ctype == b"IEND":
            break

    write_to = outpath if outpath else path
    write_to.write_bytes(bytes(out))
    return True, changed

def extract_png_text_chunks(path: Path):
    chunks = []
    data = path.read_bytes()
    if not data.startswith(PNG_SIG):
        return chunks

    i = len(PNG_SIG)
    while i < len(data):
        if i + 8 > len(data):
            break
        
        length = struct.unpack(">I", data[i:i+4])[0]
        ctype = data[i+4:i+8]
        i += 8

        if i + length + 4 > len(data):
            break

        chunkdata = data[i:i+length]
        i += length
        i += 4  # CRC

        if ctype in [b"tEXt", b"zTXt", b"iTXt"]:
            try:
                chunks.append(f"{ctype.decode()}: {chunkdata}")
            except:
                chunks.append(f"{ctype.decode()}: <binary>")

        if ctype == b"IEND":
            break

    return chunks


def anomaly_pixel_scan(img):
    pix = img.convert("RGB").getdata()
    anomalies = []
    for idx, (r, g, b) in enumerate(pix):
        if (r == 0 and g == 0 and b == 0) or (r == 255 and g == 255 and b == 255):
            anomalies.append(idx)
    return len(anomalies)


def carve_files_from_bits(bitstr):
    SIGNATURES = {
        "png": "89504e470d0a1a0a",
        "jpg": "ffd8ff",
        "zip": "504b0304",
        "gif": "47494638",
        "pdf": "25504446"
    }
    out = []
    hexstream = f"{int(bitstr, 2):x}"

    for name, sig in SIGNATURES.items():
        if sig in hexstream:
            out.append(f"Found {name.upper()} signature at offset hex index {hexstream.find(sig)}")
    return out


def extract_lsb_stream(arr, bitcount):
    bits = ""
    for v in arr:
        for b in range(bitcount):
            bits += str((v >> b) & 1)
    return bits


def save_mode(img, path, index, name, data):
    Image.frombytes("L", img.size, data).save(path / f"{index:02d}_{name}.png")


def generate_stegsolve_modes(img, out):
    rgb = img.convert("RGBA")
    w, h = rgb.size
    pixels = list(rgb.getdata())

    R = bytes([p[0] for p in pixels])
    G = bytes([p[1] for p in pixels])
    B = bytes([p[2] for p in pixels])
    A = bytes([p[3] for p in pixels])

    modes = []
    idx = 1

    modes.append(("RGB", rgb))
    modes.append(("Grayscale", ImageOps.grayscale(img)))
    modes.append(("Red", Image.frombytes("L", (w, h), R)))
    modes.append(("Green", Image.frombytes("L", (w, h), G)))
    modes.append(("Blue", Image.frombytes("L", (w, h), B)))
    modes.append(("Alpha", Image.frombytes("L", (w, h), A)))

    modes.append(("Negative", ImageOps.invert(rgb.convert("RGB"))))

    for order in [(0,1,2), (2,1,0), (1,0,2), (1,2,0), (2,0,1)]:
        arr = []
        for p in pixels:
            arr.append((p[order[0]], p[order[1]], p[order[2]]))
        modes.append((f"Shuffle_{order}", Image.new("RGB", (w,h))))

        modes[-1][1].putdata(arr)

    def xor(a,b): return a ^ b
    xor_rb = bytes([xor(r,b) for r,b in zip(R,B)])
    xor_rg = bytes([xor(r,g) for r,g in zip(R,G)])
    xor_gb = bytes([xor(g,b) for g,b in zip(G,B)])

    modes.append(("XOR_RB", Image.frombytes("L",(w,h), xor_rb)))
    modes.append(("XOR_RG", Image.frombytes("L",(w,h), xor_rg)))
    modes.append(("XOR_GB", Image.frombytes("L",(w,h), xor_gb)))

    for bit in range(1,5):
        for name, ARR in [("R",R), ("G",G), ("B",B)]:
            arr = bytes([ ((v >> (bit-1)) & 1) * 255 for v in ARR ])
            modes.append((f"LSB{bit}_{name}", Image.frombytes("L",(w,h), arr)))

    for name, im in modes:
        im.save(out / f"{idx:02d}_{name}.png")
        idx += 1


def extract_metadata(img, path):
    meta = {}
    meta["format"] = img.format
    meta["mode"] = img.mode
    meta["size"] = img.size
    meta["file_size"] = path.stat().st_size
    meta["info"] = str(img.info)
    return meta



def process_file(path: Path, out_root: Path):

    detected = detect_file_type(path)
    if not detected:
        return False, "unknown"

    if path.suffix.lower().lstrip(".") != detected:
        path = rename_with_extension(path, detected)

    try:
        img = Image.open(str(path))
    except Exception as e:
        return False, f"cannot_open:{e}"

    if img.format.lower() not in ("png","jpeg","gif","bmp","webp"):
        return False, "unsupported"

    repaired = None
    if img.format.lower() == "png":
        bak = path.with_suffix(path.suffix + ".bak")
        if not bak.exists():
            shutil.copy2(path, bak)
        fixed = path.with_name(path.stem + "_fixed" + path.suffix)
        ok, changed = repair_png_crc(path, fixed)
        if ok:
            if changed:
                fixed.replace(path)
                repaired = True
                img = Image.open(str(path))
            else:
                fixed.unlink()
                repaired = False

    out_folder = out_root / f"{path.stem}_output"
    out_folder.mkdir(parents=True, exist_ok=True)

    shutil.copy2(path, out_folder / "original.png")

    generate_stegsolve_modes(img, out_folder)

    meta = extract_metadata(img, path)
    if repaired is not None:
        meta["png_repair"] = repaired

    if img.format.lower() == "png":
        meta["png_chunks"] = extract_png_text_chunks(path)

    if hasattr(img, "getexif"):
        try:
            exif = img.getexif()
            exif_txt = {}
            for tag, val in exif.items():
                name = ExifTags.TAGS.get(tag, tag)
                exif_txt[name] = val
            meta["EXIF"] = exif_txt
        except:
            pass

    meta["pixel_anomaly_count"] = anomaly_pixel_scan(img)

    R = [p[0] for p in img.convert("RGB").getdata()]
    bits = extract_lsb_stream(R, 1)
    meta["carving"] = carve_files_from_bits(bits)

    with open(out_folder / "metadata.txt", "w", encoding="utf-8") as f:
        for k,v in meta.items():
            f.write(f"{k}: {v}\n\n")

    return True, "ok"



def main():
    base_dir = Path("./Forensik 1")
    out_root = base_dir / "stego_output"

    if not base_dir.exists():
        print("Folder 'Forensik 1' tidak ditemukan!")
        return

    out_root.mkdir(exist_ok=True)

    for f in sorted(base_dir.iterdir()):
        if f.is_dir():
            if f.name == "stego_output":
                continue
            continue

        if f.name.endswith(".bak"):
            continue

        detected = detect_file_type(f)
        if not detected:
            print(f"[REMOVE] {f.name} -> unknown")
            try: f.unlink()
            except: pass
            continue

        if detected not in ["png","jpg","jpeg","gif","bmp","webp"]:
            print(f"[REMOVE] {f.name} -> not image ({detected})")
            try: f.unlink()
            except: pass
            continue

        print(f"[PROCESS] {f.name} ({detected})")
        ok, msg = process_file(f, out_root)
        print("  ->", msg)



if __name__ == "__main__":
    main()
