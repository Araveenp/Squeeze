"""Squeeze compression engine. Never touches the original: output is always a new file beside it."""
import io, os, shutil, subprocess, zipfile
from PIL import Image, ImageOps

try:  # optional: HEIC/HEIF support
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

IMG = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}
AUDIO = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus"}
VIDEO = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


class Skip(Exception):
    """Nothing to gain (already small); not a real error."""


def out_path(src, ext=None, suffix="_compressed"):
    base, e = os.path.splitext(src.rstrip("\\/"))
    ext = ext or e
    p, n = f"{base}{suffix}{ext}", 2
    while os.path.exists(p):
        p, n = f"{base}{suffix}_{n}{ext}", n + 1
    return p


def _size(p):
    if os.path.isdir(p):
        return sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(p) for f in fs)
    return os.path.getsize(p)


def _finish(src, data, ext):
    if len(data) >= os.path.getsize(src):
        raise Skip("already as small as it gets")
    out = out_path(src, ext)
    with open(out, "wb") as f:
        f.write(data)
    return out, os.path.getsize(src), len(data)


# ---------- images ----------
def _flat(img):
    if "A" in img.getbands() or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, "white")
        bg.paste(rgba, mask=rgba.split()[3])
        return bg
    return img.convert("RGB")


def _encode(img, ext, q):
    """q = 1..100. JPEG/WebP: real quality. PNG: palette size (lossy, like TinyPNG)."""
    buf = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        img.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    elif ext == ".webp":
        img.save(buf, "WEBP", quality=q, method=6)
    else:
        n = max(8, min(256, int(256 * q / 100)))
        im = img if img.mode in ("RGB", "RGBA") else img.convert("RGBA" if "A" in img.getbands() else "RGB")
        method = Image.Quantize.FASTOCTREE if im.mode == "RGBA" else Image.Quantize.MEDIANCUT
        im.quantize(n, method=method).save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _fit(img, ext, target):
    """Highest quality that fits `target` bytes; shrinks pixels only if quality alone can't."""
    scale = 1.0
    while True:
        im = img if scale == 1 else img.resize(
            (max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
        best = _encode(im, ext, 5)
        if len(best) <= target or min(im.size) < 48:
            lo, hi = 6, 95
            while lo <= hi:
                mid = (lo + hi) // 2
                d = _encode(im, ext, mid)
                if len(d) <= target:
                    best, lo = d, mid + 1
                else:
                    hi = mid - 1
            return best
        scale *= 0.8


def compress_image(src, mode, value):
    ext = os.path.splitext(src)[1].lower()
    out_ext = ext if ext in (".jpg", ".jpeg", ".png", ".webp") else ".jpg"
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    img.load()
    if out_ext in (".jpg", ".jpeg"):
        img = _flat(img)
    data = _encode(img, out_ext, int(value)) if mode == "quality" else _fit(img, out_ext, int(value))
    return _finish(src, data, out_ext)


# ---------- pdf ----------
def compress_pdf(src, mode, value):
    import pymupdf

    def attempt(q):
        doc = pymupdf.open(src)
        try:
            dpi = max(60, int(q * 1.5))
            try:
                doc.rewrite_images(dpi_threshold=dpi + 40, dpi_target=dpi, quality=q)
            except AttributeError:  # older PyMuPDF: structural clean-up only
                pass
            return doc.tobytes(garbage=4, deflate=True, clean=True)
        finally:
            doc.close()

    if mode == "quality":
        data = attempt(int(value))
    else:
        for q in (85, 70, 55, 40, 25, 12):
            data = attempt(q)
            if len(data) <= value:
                break
    return _finish(src, data, ".pdf")


# ---------- audio / video (needs ffmpeg on PATH) ----------
def _tool(name):
    p = shutil.which(name)
    if not p:
        raise RuntimeError("ffmpeg isn't installed. Run: winget install Gyan.FFmpeg")
    return p


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode:
        lines = r.stderr.strip().splitlines()
        raise RuntimeError(lines[-1] if lines else "ffmpeg failed")
    return r.stdout.strip()


def compress_media(src, mode, value, video):
    ff, probe = _tool("ffmpeg"), _tool("ffprobe")
    out = out_path(src, ".mp4" if video else ".mp3")
    if mode == "size":
        dur = float(_run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", src]))
        total = value * 8 / dur / 1000 * 0.95  # kbps, with ~5% container headroom
        a_kbps = 96 if video else max(16, min(320, int(total)))
        v_kbps = max(50, int(total - a_kbps))
        v_args = ["-b:v", f"{v_kbps}k", "-maxrate", f"{int(v_kbps * 1.5)}k", "-bufsize", f"{v_kbps * 2}k"]
    else:
        a_kbps = {40: 64, 65: 128, 85: 192}.get(int(value), 128)
        v_args = ["-crf", str({40: 32, 65: 27, 85: 23}.get(int(value), 27))]
    if video:
        cmd = [ff, "-y", "-i", src, "-c:v", "libx264", "-preset", "medium", *v_args,
               "-c:a", "aac", "-b:a", f"{a_kbps}k", "-movflags", "+faststart", out]
    else:
        cmd = [ff, "-y", "-i", src, "-vn", "-c:a", "libmp3lame", "-b:a", f"{a_kbps}k", out]
    try:
        _run(cmd)
        if os.path.getsize(out) >= os.path.getsize(src):
            raise Skip("already as small as it gets")
    except Exception:
        if os.path.exists(out):
            os.remove(out)
        raise
    return out, os.path.getsize(src), os.path.getsize(out)


# ---------- zip ----------
def make_zip(paths):
    first = paths[0]
    out = out_path(first if len(paths) == 1 else os.path.join(os.path.dirname(first), "Archive"), ".zip", "")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in paths:
            if os.path.isdir(p):
                root = os.path.dirname(p.rstrip("\\/"))
                for d, _, fs in os.walk(p):
                    for f in fs:
                        fp = os.path.join(d, f)
                        z.write(fp, os.path.relpath(fp, root))
            else:
                z.write(p, os.path.basename(p))
    return out, sum(_size(p) for p in paths), os.path.getsize(out)


# ---------- entry points ----------
def compress_one(p, mode, value):
    if os.path.isdir(p):
        return make_zip([p])
    ext = os.path.splitext(p)[1].lower()
    if mode == "size" and os.path.getsize(p) <= value:
        raise Skip("already under that size")
    if ext in IMG:
        return compress_image(p, mode, value)
    if ext == ".pdf":
        return compress_pdf(p, mode, value)
    if ext in AUDIO | VIDEO:
        return compress_media(p, mode, value, ext in VIDEO)
    return make_zip([p])  # anything else: zip it


def run(paths, mode, value):
    """-> (results, errors). results = [(out_path, size_before, size_after)]"""
    if mode == "zip":
        try:
            return [make_zip(paths)], []
        except Exception as e:
            return [], [str(e)]
    results, errors = [], []
    for p in paths:
        try:
            results.append(compress_one(p, mode, value))
        except Exception as e:
            errors.append(f"{os.path.basename(p.rstrip(chr(92) + '/'))}: {e}")
    return results, errors
