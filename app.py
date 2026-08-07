from flask import Flask, render_template, request, send_file
import qrcode
import io
import os
import json
import base64
import urllib.parse
import uuid
import difflib
import subprocess
from pdf2docx import Converter
import fitz  # PyMuPDF
import zipfile
import tempfile
from PIL import Image
from rembg import remove
from pydub import AudioSegment
from pypdf import PdfReader, PdfWriter

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB max upload size

# ---------- Home Page ----------
@app.route("/")
def home():
    return render_template("index.html")


# ---------- 1. Word / Character Counter ----------
@app.route("/word-counter", methods=["GET", "POST"])
def word_counter():
    result = None
    text = ""
    if request.method == "POST":
        text = request.form.get("text", "")
        words = len(text.split())
        chars = len(text)
        chars_no_space = len(text.replace(" ", ""))
        sentences = text.count(".") + text.count("!") + text.count("?")
        result = {
            "words": words,
            "chars": chars,
            "chars_no_space": chars_no_space,
            "sentences": sentences,
        }
    return render_template("word_counter.html", result=result, text=text)


# ---------- 2. QR Code Generator ----------
@app.route("/qr-generator", methods=["GET", "POST"])
def qr_generator():
    if request.method == "POST":
        data = request.form.get("qr_text", "")
        if data:
            img = qrcode.make(data)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="qrcode.png")
    return render_template("qr_generator.html")


# ---------- 3. Unit Converter ----------
CONVERSIONS = {
    "length": {
        "meter": 1.0, "kilometer": 1000.0, "centimeter": 0.01,
        "mile": 1609.34, "yard": 0.9144, "foot": 0.3048, "inch": 0.0254,
    },
    "weight": {
        "kilogram": 1.0, "gram": 0.001, "milligram": 0.000001,
        "pound": 0.453592, "ounce": 0.0283495,
    },
}

@app.route("/unit-converter", methods=["GET", "POST"])
def unit_converter():
    result = None
    category = "length"
    from_unit = to_unit = None
    value = 0
    if request.method == "POST":
        category = request.form.get("category", "length")
        from_unit = request.form.get("from_unit")
        to_unit = request.form.get("to_unit")
        try:
            value = float(request.form.get("value", 0))
            base = value * CONVERSIONS[category][from_unit]
            result = base / CONVERSIONS[category][to_unit]
        except (ValueError, KeyError, ZeroDivisionError):
            result = "Invalid input"
    return render_template(
        "unit_converter.html",
        conversions=CONVERSIONS,
        category=category,
        result=result,
        from_unit=from_unit,
        to_unit=to_unit,
        value=value,
    )


# ---------- 4. Temperature Converter ----------
@app.route("/temperature-converter", methods=["GET", "POST"])
def temperature_converter():
    result = None
    value = 0
    from_unit = to_unit = "Celsius"
    if request.method == "POST":
        from_unit = request.form.get("from_unit")
        to_unit = request.form.get("to_unit")
        try:
            value = float(request.form.get("value", 0))
            if from_unit == "Fahrenheit":
                celsius = (value - 32) * 5 / 9
            elif from_unit == "Kelvin":
                celsius = value - 273.15
            else:
                celsius = value

            if to_unit == "Fahrenheit":
                result = celsius * 9 / 5 + 32
            elif to_unit == "Kelvin":
                result = celsius + 273.15
            else:
                result = celsius
        except ValueError:
            result = "Invalid input"
    return render_template(
        "temperature_converter.html",
        result=result, value=value, from_unit=from_unit, to_unit=to_unit
    )


# ---------- 5. Image Compressor ----------
@app.route("/image-compressor", methods=["GET", "POST"])
def image_compressor():
    if request.method == "POST":
        file = request.files.get("image")
        target_size = request.form.get("target_size")
        size_unit = request.form.get("size_unit", "KB")

        if file and target_size:
            img = Image.open(file.stream).convert("RGB")

            target_kb = float(target_size)
            if size_unit == "MB":
                target_kb = target_kb * 1024

            target_bytes = target_kb * 1024
            low, high = 5, 95
            best_buf = None

            for _ in range(8):
                mid = (low + high) // 2
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=mid, optimize=True)
                size = buf.tell()

                if size <= target_bytes:
                    best_buf = buf
                    low = mid + 1
                else:
                    high = mid - 1

            if best_buf is None:
                best_buf = io.BytesIO()
                img.save(best_buf, format="JPEG", quality=5, optimize=True)

            best_buf.seek(0)
            return send_file(best_buf, mimetype="image/jpeg",
                              as_attachment=True, download_name="compressed.jpg")

    return render_template("image_compressor.html")


# ---------- 6. Percentage Calculator ----------
@app.route("/percentage-calculator", methods=["GET", "POST"])
def percentage_calculator():
    result = None
    calc_type = "percent_of"
    value1 = value2 = None

    if request.method == "POST":
        calc_type = request.form.get("calc_type", "percent_of")
        try:
            value1 = float(request.form.get("value1", 0))
            value2 = float(request.form.get("value2", 0))

            if calc_type == "percent_of":
                result = (value1 / 100) * value2
            elif calc_type == "is_what_percent":
                result = (value1 / value2) * 100 if value2 != 0 else "Invalid input"
            elif calc_type == "percent_change":
                result = ((value2 - value1) / value1) * 100 if value1 != 0 else "Invalid input"
        except (ValueError, ZeroDivisionError):
            result = "Invalid input"

    return render_template(
        "percentage_calculator.html",
        result=result, calc_type=calc_type, value1=value1, value2=value2
    )


# ---------- 7. Password Generator ----------
import random
import string

@app.route("/password-generator", methods=["GET", "POST"])
def password_generator():
    password = None
    length = 12
    use_upper = use_lower = use_numbers = use_symbols = True

    if request.method == "POST":
        try:
            length = int(request.form.get("length", 12))
            length = max(4, min(length, 64))
        except ValueError:
            length = 12

        use_upper = request.form.get("use_upper") == "on"
        use_lower = request.form.get("use_lower") == "on"
        use_numbers = request.form.get("use_numbers") == "on"
        use_symbols = request.form.get("use_symbols") == "on"

        char_pool = ""
        if use_upper:
            char_pool += string.ascii_uppercase
        if use_lower:
            char_pool += string.ascii_lowercase
        if use_numbers:
            char_pool += string.digits
        if use_symbols:
            char_pool += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if char_pool:
            password = "".join(random.SystemRandom().choice(char_pool) for _ in range(length))
        else:
            password = "Select at least one character type"

    return render_template(
        "password_generator.html",
        password=password, length=length,
        use_upper=use_upper, use_lower=use_lower,
        use_numbers=use_numbers, use_symbols=use_symbols
    )

# ---------- 8. Word to PDF ----------
@app.route("/word-to-pdf", methods=["GET", "POST"])
def word_to_pdf():
    if request.method == "POST":
        file = request.files.get("docx_file")
        if not file or file.filename == "":
            return render_template("word_to_pdf.html", error="Please select a Word file.")
        if not file.filename.lower().endswith((".docx", ".doc")):
            return render_template("word_to_pdf.html", error="Please upload a .docx or .doc file.")

        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)

        output_filename = os.path.splitext(file.filename)[0] + ".pdf"
        output_path = os.path.join(temp_dir, output_filename)

        try:
            try:
                subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "pdf",
                     "--outdir", temp_dir, input_path],
                    check=True, timeout=60
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                subprocess.run(
                    ["soffice", "--headless", "--convert-to", "pdf",
                     "--outdir", temp_dir, input_path],
                    check=True, timeout=60
                )
        except Exception:
            return render_template("word_to_pdf.html", error="Conversion failed. Please try again.")

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    return render_template("word_to_pdf.html")


# ---------- 9. PDF to Word ----------
@app.route("/pdf-to-word", methods=["GET", "POST"])
def pdf_to_word():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        if not file or file.filename == "":
            return render_template("pdf_to_word.html", error="Please select a PDF file.")
        if not file.filename.lower().endswith(".pdf"):
            return render_template("pdf_to_word.html", error="Please upload a .pdf file.")

        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)

        output_filename = os.path.splitext(file.filename)[0] + ".docx"
        output_path = os.path.join(temp_dir, output_filename)

        try:
            cv = Converter(input_path)
            cv.convert(output_path)
            cv.close()
        except Exception:
            return render_template("pdf_to_word.html", error="Conversion failed. Please try again.")

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    return render_template("pdf_to_word.html")


# ---------- 10. PDF to JPG ----------
@app.route("/pdf-to-jpg", methods=["GET", "POST"])
def pdf_to_jpg():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        if not file or file.filename == "":
            return render_template("pdf_to_jpg.html", error="Please select a PDF file.")
        if not file.filename.lower().endswith(".pdf"):
            return render_template("pdf_to_jpg.html", error="Please upload a .pdf file.")

        try:
            pdf_bytes = file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            if doc.page_count == 1:
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=150)
                img_buf = io.BytesIO(pix.tobytes("jpg"))
                img_buf.seek(0)
                doc.close()
                return send_file(img_buf, mimetype="image/jpeg",
                                  as_attachment=True, download_name="converted.jpg")
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    for i in range(doc.page_count):
                        page = doc.load_page(i)
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("jpg")
                        zf.writestr(f"page_{i+1}.jpg", img_bytes)
                doc.close()
                zip_buf.seek(0)
                return send_file(zip_buf, mimetype="application/zip",
                                  as_attachment=True, download_name="converted_pages.zip")
        except Exception:
            return render_template("pdf_to_jpg.html", error="Conversion failed. Please try again.")

    return render_template("pdf_to_jpg.html")


# ---------- 11. JPG to PDF ----------
@app.route("/jpg-to-pdf", methods=["GET", "POST"])
def jpg_to_pdf():
    if request.method == "POST":
        files = request.files.getlist("images")
        images = []
        for f in files:
            if f and f.filename:
                img = Image.open(f.stream).convert("RGB")
                images.append(img)

        if images:
            buf = io.BytesIO()
            images[0].save(
                buf, format="PDF", save_all=True,
                append_images=images[1:]
            )
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="converted.pdf")
        return render_template("jpg_to_pdf.html", error="Please select at least one image.")

    return render_template("jpg_to_pdf.html")


# ---------- 12. JPG to PNG ----------
@app.route("/jpg-to-png", methods=["GET", "POST"])
def jpg_to_png():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("jpg_to_png.html", error="Please select a JPG image.")
        try:
            img = Image.open(file.stream).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="converted.png")
        except Exception:
            return render_template("jpg_to_png.html", error="Conversion failed. Please try again.")
    return render_template("jpg_to_png.html")


# ---------- 13. PNG to JPG ----------
@app.route("/png-to-jpg", methods=["GET", "POST"])
def png_to_jpg():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("png_to_jpg.html", error="Please select a PNG image.")
        try:
            img = Image.open(file.stream).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg",
                              as_attachment=True, download_name="converted.jpg")
        except Exception:
            return render_template("png_to_jpg.html", error="Conversion failed. Please try again.")
    return render_template("png_to_jpg.html")


# ---------- 14. WEBP to JPG ----------
@app.route("/webp-to-jpg", methods=["GET", "POST"])
def webp_to_jpg():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("webp_to_jpg.html", error="Please select a WEBP image.")
        try:
            img = Image.open(file.stream).convert("RGB")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=95)
            buf.seek(0)
            return send_file(buf, mimetype="image/jpeg",
                              as_attachment=True, download_name="converted.jpg")
        except Exception:
            return render_template("webp_to_jpg.html", error="Conversion failed. Please try again.")
    return render_template("webp_to_jpg.html")

# ---------- 15. Background Remover ----------
@app.route("/background-remover", methods=["GET", "POST"])
def background_remover():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return {"error": "Please select an image."}, 400
        try:
            input_bytes = file.read()
            output_bytes = remove(input_bytes)
            buf = io.BytesIO(output_bytes)
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="no_background.png")
        except Exception:
            return {"error": "Background removal failed. Please try again."}, 500
    return render_template("background_remover.html")

# ---------- 16. Audio Converter ----------
app.config['MAX_AUDIO_LENGTH'] = 20 * 60 * 1000  # 20 minutes in milliseconds

ALLOWED_AUDIO_FORMATS = ["mp3", "wav", "aac", "flac", "ogg"]

@app.route("/audio-converter", methods=["GET", "POST"])
def audio_converter():
    if request.method == "POST":
        file = request.files.get("audio")
        target_format = request.form.get("target_format", "mp3")

        if not file or file.filename == "":
            return render_template("audio_converter.html", error="Please select an audio file.")

        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_AUDIO_FORMATS:
            return render_template("audio_converter.html",
                                    error="Unsupported file type. Allowed: MP3, WAV, AAC, FLAC, OGG.")

        if target_format not in ALLOWED_AUDIO_FORMATS:
            return render_template("audio_converter.html", error="Invalid target format selected.")

        try:
            audio = AudioSegment.from_file(file.stream, format=ext)

            if len(audio) > app.config['MAX_AUDIO_LENGTH']:
                return render_template("audio_converter.html",
                                        error="Audio is too long. Max allowed length is 20 minutes.")

            buf = io.BytesIO()
            export_format = "mp4" if target_format == "aac" else target_format
            audio.export(buf, format=export_format)
            buf.seek(0)

            mime_map = {
                "mp3": "audio/mpeg", "wav": "audio/wav", "aac": "audio/aac",
                "flac": "audio/flac", "ogg": "audio/ogg"
            }

            return send_file(buf, mimetype=mime_map.get(target_format, "audio/mpeg"),
                              as_attachment=True, download_name=f"converted.{target_format}")
        except Exception:
            return render_template("audio_converter.html",
                                    error="Conversion failed. Please try a different file.")

    return render_template("audio_converter.html")


# ---------- 17. Merge PDF ----------
@app.route("/merge-pdf", methods=["GET", "POST"])
def merge_pdf():
    if request.method == "POST":
        files = request.files.getlist("pdfs")
        pdf_files = [f for f in files if f and f.filename]
        if len(pdf_files) < 2:
            return render_template("merge_pdf.html", error="Please select at least 2 PDF files.")
        try:
            writer = PdfWriter()
            for f in pdf_files:
                reader = PdfReader(f.stream)
                for page in reader.pages:
                    writer.add_page(page)
            buf = io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="merged.pdf")
        except Exception:
            return render_template("merge_pdf.html", error="Merge failed. Please check your files.")
    return render_template("merge_pdf.html")


# ---------- 18. Split PDF ----------
@app.route("/split-pdf", methods=["GET", "POST"])
def split_pdf():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        if not file or file.filename == "":
            return render_template("split_pdf.html", error="Please select a PDF file.")
        try:
            reader = PdfReader(file.stream)
            if len(reader.pages) < 2:
                return render_template("split_pdf.html", error="PDF must have at least 2 pages to split.")

            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for i, page in enumerate(reader.pages):
                    writer = PdfWriter()
                    writer.add_page(page)
                    page_buf = io.BytesIO()
                    writer.write(page_buf)
                    zf.writestr(f"page_{i+1}.pdf", page_buf.getvalue())
            zip_buf.seek(0)
            return send_file(zip_buf, mimetype="application/zip",
                              as_attachment=True, download_name="split_pages.zip")
        except Exception:
            return render_template("split_pdf.html", error="Split failed. Please try again.")
    return render_template("split_pdf.html")


# ---------- 19. Compress PDF ----------
@app.route("/compress-pdf", methods=["GET", "POST"])
def compress_pdf():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        if not file or file.filename == "":
            return render_template("compress_pdf.html", error="Please select a PDF file.")
        try:
            pdf_bytes = file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            buf = io.BytesIO()
            doc.save(buf, garbage=4, deflate=True, clean=True)
            doc.close()
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="compressed.pdf")
        except Exception:
            return render_template("compress_pdf.html", error="Compression failed. Please try again.")
    return render_template("compress_pdf.html")


# ---------- 20. Rotate PDF ----------
@app.route("/rotate-pdf", methods=["GET", "POST"])
def rotate_pdf():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        try:
            angle = int(request.form.get("angle", 90))
        except ValueError:
            angle = 90

        if not file or file.filename == "":
            return render_template("rotate_pdf.html", error="Please select a PDF file.")
        try:
            reader = PdfReader(file.stream)
            writer = PdfWriter()
            for page in reader.pages:
                page.rotate(angle)
                writer.add_page(page)
            buf = io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="rotated.pdf")
        except Exception:
            return render_template("rotate_pdf.html", error="Rotation failed. Please try again.")
    return render_template("rotate_pdf.html")


# ---------- 21. Unlock PDF ----------
@app.route("/unlock-pdf", methods=["GET", "POST"])
def unlock_pdf():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        password = request.form.get("password", "")

        if not file or file.filename == "":
            return render_template("unlock_pdf.html", error="Please select a PDF file.")
        try:
            reader = PdfReader(file.stream)
            if reader.is_encrypted:
                result = reader.decrypt(password)
                if result == 0:
                    return render_template("unlock_pdf.html", error="Incorrect password. Please try again.")

            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            buf = io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="unlocked.pdf")
        except Exception:
            return render_template("unlock_pdf.html", error="Unlock failed. Please check your password.")
    return render_template("unlock_pdf.html")


# ---------- 22. Protect PDF ----------
@app.route("/protect-pdf", methods=["GET", "POST"])
def protect_pdf():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        password = request.form.get("password", "")

        if not file or file.filename == "":
            return render_template("protect_pdf.html", error="Please select a PDF file.")
        if not password:
            return render_template("protect_pdf.html", error="Please enter a password.")
        try:
            reader = PdfReader(file.stream)
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(password)
            buf = io.BytesIO()
            writer.write(buf)
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="protected.pdf")
        except Exception:
            return render_template("protect_pdf.html", error="Protection failed. Please try again.")
    return render_template("protect_pdf.html")


# ---------- 23. PDF to PNG ----------
@app.route("/pdf-to-png", methods=["GET", "POST"])
def pdf_to_png():
    if request.method == "POST":
        file = request.files.get("pdf_file")
        if not file or file.filename == "":
            return render_template("pdf_to_png.html", error="Please select a PDF file.")
        if not file.filename.lower().endswith(".pdf"):
            return render_template("pdf_to_png.html", error="Please upload a .pdf file.")

        try:
            pdf_bytes = file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            if doc.page_count == 1:
                page = doc.load_page(0)
                pix = page.get_pixmap(dpi=150)
                img_buf = io.BytesIO(pix.tobytes("png"))
                img_buf.seek(0)
                doc.close()
                return send_file(img_buf, mimetype="image/png",
                                  as_attachment=True, download_name="converted.png")
            else:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w") as zf:
                    for i in range(doc.page_count):
                        page = doc.load_page(i)
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        zf.writestr(f"page_{i+1}.png", img_bytes)
                doc.close()
                zip_buf.seek(0)
                return send_file(zip_buf, mimetype="application/zip",
                                  as_attachment=True, download_name="converted_pages.zip")
        except Exception:
            return render_template("pdf_to_png.html", error="Conversion failed. Please try again.")

    return render_template("pdf_to_png.html")


# ---------- 24. PNG to PDF ----------
@app.route("/png-to-pdf", methods=["GET", "POST"])
def png_to_pdf():
    if request.method == "POST":
        files = request.files.getlist("images")
        images = []
        for f in files:
            if f and f.filename:
                img = Image.open(f.stream).convert("RGB")
                images.append(img)

        if images:
            buf = io.BytesIO()
            images[0].save(
                buf, format="PDF", save_all=True,
                append_images=images[1:]
            )
            buf.seek(0)
            return send_file(buf, mimetype="application/pdf",
                              as_attachment=True, download_name="converted.pdf")
        return render_template("png_to_pdf.html", error="Please select at least one image.")

    return render_template("png_to_pdf.html")


# ---------- 25. JSON Formatter ----------
@app.route("/json-formatter", methods=["GET", "POST"])
def json_formatter():
    result = None
    input_text = ""
    error = None
    if request.method == "POST":
        input_text = request.form.get("json_input", "")
        try:
            parsed = json.loads(input_text)
            result = json.dumps(parsed, indent=4)
        except Exception as e:
            error = "Invalid JSON: " + str(e)
    return render_template("json_formatter.html", result=result, input_text=input_text, error=error)


# ---------- 26. Base64 Encode/Decode ----------
@app.route("/base64-tool", methods=["GET", "POST"])
def base64_tool():
    result = None
    input_text = ""
    mode = "encode"
    error = None
    if request.method == "POST":
        input_text = request.form.get("text_input", "")
        mode = request.form.get("mode", "encode")
        try:
            if mode == "encode":
                result = base64.b64encode(input_text.encode("utf-8")).decode("utf-8")
            else:
                result = base64.b64decode(input_text.encode("utf-8")).decode("utf-8")
        except Exception:
            error = "Invalid input for " + mode + "ing."
    return render_template("base64_tool.html", result=result, input_text=input_text, mode=mode, error=error)


# ---------- 27. URL Encoder/Decoder ----------
@app.route("/url-encoder", methods=["GET", "POST"])
def url_encoder():
    result = None
    input_text = ""
    mode = "encode"
    error = None
    if request.method == "POST":
        input_text = request.form.get("text_input", "")
        mode = request.form.get("mode", "encode")
        try:
            if mode == "encode":
                result = urllib.parse.quote(input_text)
            else:
                result = urllib.parse.unquote(input_text)
        except Exception:
            error = "Invalid input for " + mode + "ing."
    return render_template("url_encoder.html", result=result, input_text=input_text, mode=mode, error=error)


# ---------- 28. UUID Generator ----------
@app.route("/uuid-generator", methods=["GET", "POST"])
def uuid_generator():
    uuids = []
    count = 1
    if request.method == "POST":
        try:
            count = int(request.form.get("count", 1))
            count = max(1, min(count, 50))
        except ValueError:
            count = 1
        uuids = [str(uuid.uuid4()) for _ in range(count)]
    return render_template("uuid_generator.html", uuids=uuids, count=count)


# ---------- 29. Case Converter ----------
@app.route("/case-converter", methods=["GET", "POST"])
def case_converter():
    result = None
    input_text = ""
    case_type = "upper"
    if request.method == "POST":
        input_text = request.form.get("text_input", "")
        case_type = request.form.get("case_type", "upper")

        if case_type == "upper":
            result = input_text.upper()
        elif case_type == "lower":
            result = input_text.lower()
        elif case_type == "title":
            result = input_text.title()
        elif case_type == "sentence":
            result = ". ".join(s.strip().capitalize() for s in input_text.split(".") if s.strip())
            if input_text.strip().endswith("."):
                result += "."
        elif case_type == "capitalize":
            result = input_text.capitalize()
        elif case_type == "alternating":
            result = "".join(
                c.upper() if i % 2 == 0 else c.lower()
                for i, c in enumerate(input_text)
            )
        else:
            result = input_text

    return render_template("case_converter.html", result=result, input_text=input_text, case_type=case_type)


# ---------- 30. Remove Duplicate Lines ----------
@app.route("/remove-duplicate-lines", methods=["GET", "POST"])
def remove_duplicate_lines():
    result = None
    input_text = ""
    removed_count = 0
    if request.method == "POST":
        input_text = request.form.get("text_input", "")
        lines = input_text.splitlines()
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                seen.add(line)
                unique_lines.append(line)
        removed_count = len(lines) - len(unique_lines)
        result = "\n".join(unique_lines)

    return render_template("remove_duplicate_lines.html", result=result, input_text=input_text, removed_count=removed_count)


# ---------- 31. Text Compare ----------
@app.route("/text-compare", methods=["GET", "POST"])
def text_compare():
    result = None
    text_a = ""
    text_b = ""
    if request.method == "POST":
        text_a = request.form.get("text_a", "")
        text_b = request.form.get("text_b", "")

        lines_a = text_a.splitlines()
        lines_b = text_b.splitlines()

        diff = list(difflib.unified_diff(lines_a, lines_b, lineterm=""))
        result = "\n".join(diff) if diff else "No differences found. Both texts are identical."

    return render_template("text_compare.html", result=result, text_a=text_a, text_b=text_b)



# ---------- 32. Crop Image ----------
from PIL import ImageFilter

@app.route("/crop-image", methods=["GET", "POST"])
def crop_image():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("crop_image.html", error="Please select an image.")
        try:
            x = int(request.form.get("x", 0))
            y = int(request.form.get("y", 0))
            width = int(request.form.get("width", 100))
            height = int(request.form.get("height", 100))

            img = Image.open(file.stream)
            img_w, img_h = img.size

            x = max(0, min(x, img_w))
            y = max(0, min(y, img_h))
            right = max(x, min(x + width, img_w))
            bottom = max(y, min(y + height, img_h))

            cropped = img.crop((x, y, right, bottom))
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="cropped.png")
        except Exception:
            return render_template("crop_image.html", error="Crop failed. Please check your inputs.")
    return render_template("crop_image.html")


# ---------- 33. Resize Image ----------
@app.route("/resize-image", methods=["GET", "POST"])
def resize_image():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("resize_image.html", error="Please select an image.")
        try:
            width = int(request.form.get("width", 0))
            height = int(request.form.get("height", 0))
            keep_ratio = request.form.get("keep_ratio") == "on"

            img = Image.open(file.stream)

            if keep_ratio:
                img.thumbnail((width, height))
                resized = img
            else:
                resized = img.resize((max(1, width), max(1, height)))

            buf = io.BytesIO()
            resized.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="resized.png")
        except Exception:
            return render_template("resize_image.html", error="Resize failed. Please check your inputs.")
    return render_template("resize_image.html")


# ---------- 34. Watermark Image ----------
from PIL import ImageDraw, ImageFont

@app.route("/watermark-image", methods=["GET", "POST"])
def watermark_image():
    if request.method == "POST":
        file = request.files.get("image")
        watermark_text = request.form.get("watermark_text", "")
        if not file or file.filename == "":
            return render_template("watermark_image.html", error="Please select an image.")
        if not watermark_text:
            return render_template("watermark_image.html", error="Please enter watermark text.")
        try:
            img = Image.open(file.stream).convert("RGBA")
            overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)

            font_size = max(20, img.size[0] // 20)
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            pos = (img.size[0] - text_w - 20, img.size[1] - text_h - 20)

            draw.text(pos, watermark_text, font=font, fill=(255, 255, 255, 160))
            watermarked = Image.alpha_composite(img, overlay).convert("RGB")

            buf = io.BytesIO()
            watermarked.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="watermarked.png")
        except Exception:
            return render_template("watermark_image.html", error="Watermarking failed. Please try again.")
    return render_template("watermark_image.html")


# ---------- 35. Blur Image ----------
@app.route("/blur-image", methods=["GET", "POST"])
def blur_image():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("blur_image.html", error="Please select an image.")
        try:
            blur_level = int(request.form.get("blur_level", 5))
            blur_level = max(1, min(blur_level, 30))

            img = Image.open(file.stream).convert("RGB")
            blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_level))

            buf = io.BytesIO()
            blurred.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="blurred.png")
        except Exception:
            return render_template("blur_image.html", error="Blur failed. Please try again.")
    return render_template("blur_image.html")


# ---------- 36. Rotate Image ----------
@app.route("/rotate-image", methods=["GET", "POST"])
def rotate_image():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or file.filename == "":
            return render_template("rotate_image.html", error="Please select an image.")
        try:
            angle = int(request.form.get("angle", 90))
            img = Image.open(file.stream).convert("RGB")
            rotated = img.rotate(-angle, expand=True)

            buf = io.BytesIO()
            rotated.save(buf, format="PNG")
            buf.seek(0)
            return send_file(buf, mimetype="image/png",
                              as_attachment=True, download_name="rotated.png")
        except Exception:
            return render_template("rotate_image.html", error="Rotation failed. Please try again.")
    return render_template("rotate_image.html")

# ---------- 37. Markdown to HTML ----------
@app.route("/markdown-to-html")
def markdown_to_html():
    return render_template("markdown_to_html.html")

# ---------- 38. CSV to JSON ----------
@app.route("/csv-to-json")
def csv_to_json():
    return render_template("csv_to_json.html")

# ---------- 39. Color Picker ----------
@app.route("/color-picker")
def color_picker():
    return render_template("color_picker.html")

# ---------- 40. Text to Speech ----------
@app.route("/text-to-speech")
def text_to_speech():
    return render_template("text_to_speech.html")

# ---------- 41. Random Number Generator ----------
@app.route("/random-number-generator")
def random_number_generator():
    return render_template("random_number_generator.html")

# ---------- 42. Age Calculator ----------
@app.route("/age-calculator")
def age_calculator():
    return render_template("age_calculator.html")

# ---------- 43. EMI Calculator ----------
@app.route("/emi-calculator")
def emi_calculator():
    return render_template("emi_calculator.html")

# ---------- 44. Currency Converter ----------
@app.route("/currency-converter")
def currency_converter():
    return render_template("currency_converter.html")

# ---------- 45. Image to Base64 ----------
@app.route("/image-to-base64")
def image_to_base64():
    return render_template("image_to_base64.html")

# ---------- 46. Meta Tag Generator ----------
@app.route("/meta-tag-generator")
def meta_tag_generator():
    return render_template("meta_tag_generator.html")

# ---------- 47. Lorem Ipsum Generator ----------
@app.route("/lorem-ipsum-generator")
def lorem_ipsum_generator():
    return render_template("lorem_ipsum_generator.html")

# ---------- 48. HTML Minifier ----------
@app.route("/html-minifier")
def html_minifier():
    return render_template("html_minifier.html")

# ---------- 49. CSS Minifier ----------
@app.route("/css-minifier")
def css_minifier():
    return render_template("css_minifier.html")

# ---------- 50. Excel to PDF ----------
@app.route("/excel-to-pdf", methods=["GET", "POST"])
def excel_to_pdf():
    if request.method == "POST":
        file = request.files.get("excel_file")
        if not file or file.filename == "":
            return render_template("excel_to_pdf.html", error="Please select an Excel file.")
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            return render_template("excel_to_pdf.html", error="Please upload a .xlsx or .xls file.")

        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        file.save(input_path)

        output_filename = os.path.splitext(file.filename)[0] + ".pdf"
        output_path = os.path.join(temp_dir, output_filename)

        try:
            try:
                subprocess.run(
                    ["libreoffice", "--headless", "--convert-to", "pdf",
                     "--outdir", temp_dir, input_path],
                    check=True, timeout=60
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                subprocess.run(
                    ["soffice", "--headless", "--convert-to", "pdf",
                     "--outdir", temp_dir, input_path],
                    check=True, timeout=60
                )
        except Exception:
            return render_template("excel_to_pdf.html", error="Conversion failed. Please try again.")

        return send_file(output_path, as_attachment=True, download_name=output_filename)

    return render_template("excel_to_pdf.html")

# ---------- 51. Barcode Generator ----------
@app.route("/barcode-generator")
def barcode_generator():
    return render_template("barcode_generator.html")

# ---------- Privacy Policy ----------
@app.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


# ---------- About Us ----------
@app.route("/about")
def about():
    return render_template("about.html")

# ---------- Error Handler: File too large ----------
@app.errorhandler(413)
def file_too_large(e):
    return render_template("error.html", message="File is too large. Max allowed size is 32 MB."), 413


if __name__ == "__main__":
    app.run(debug=False)