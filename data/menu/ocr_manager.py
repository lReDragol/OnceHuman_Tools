import os
import shutil
import subprocess
import sys
import time
from urllib.request import urlretrieve

import pytesseract


REQUIRED_OCR_LANGUAGES = ("eng", "rus")
DEFAULT_OCR_LANGUAGES = REQUIRED_OCR_LANGUAGES
TESSERACT_PACKAGE_IDS = (
    "tesseract-ocr.tesseract",
    "UB-Mannheim.TesseractOCR",
)
LANGUAGE_URL_TEMPLATES = (
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{lang}.traineddata",
    "https://raw.githubusercontent.com/tesseract-ocr/tessdata/main/{lang}.traineddata",
)


def _deduplicate(values):
    seen = set()
    result = []
    for value in values:
        if not value:
            continue
        normalized = os.path.normpath(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _candidate_tesseract_paths():
    candidates = [
        os.getenv("TESSERACT_CMD"),
        getattr(pytesseract.pytesseract, "tesseract_cmd", None),
        shutil.which("tesseract"),
    ]
    if sys.platform.startswith("win"):
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates.extend(
            [
                os.path.join(program_files, "Tesseract-OCR", "tesseract.exe"),
                os.path.join(program_files_x86, "Tesseract-OCR", "tesseract.exe"),
                os.path.join(local_app_data, "Programs", "Tesseract-OCR", "tesseract.exe"),
                os.path.join(local_app_data, "Microsoft", "WinGet", "Links", "tesseract.exe"),
            ]
        )
    else:
        candidates.extend(("/usr/bin/tesseract", "/usr/local/bin/tesseract"))
    return _deduplicate(candidates)


def resolve_tesseract_cmd():
    for candidate in _candidate_tesseract_paths():
        if os.path.isfile(candidate):
            return candidate
    return None


def configure_tesseract_cmd():
    executable = resolve_tesseract_cmd()
    if executable:
        pytesseract.pytesseract.tesseract_cmd = executable
    return executable


def get_tessdata_dir(executable=None):
    executable = executable or configure_tesseract_cmd()
    if not executable:
        return None

    executable_dir = os.path.dirname(executable)
    candidates = [
        os.path.join(executable_dir, "tessdata"),
        os.path.join(os.path.dirname(executable_dir), "share", "tessdata"),
    ]
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return candidates[0]


def inspect_tesseract(required_languages=REQUIRED_OCR_LANGUAGES):
    executable = configure_tesseract_cmd()
    if not executable:
        return {
            "installed": False,
            "ready": False,
            "executable": None,
            "executable_path": None,
            "available_languages": [],
            "missing_languages": list(required_languages),
            "error": "Tesseract executable not found.",
        }

    try:
        pytesseract.get_tesseract_version()
    except Exception as exc:
        return {
            "installed": True,
            "ready": False,
            "executable": executable,
            "executable_path": executable,
            "available_languages": [],
            "missing_languages": list(required_languages),
            "error": str(exc),
        }

    available_languages = []
    error_message = ""
    try:
        available_languages = sorted(set(pytesseract.get_languages(config="")))
    except Exception as exc:
        error_message = str(exc)

    missing_languages = [
        language for language in required_languages if language not in available_languages
    ]
    ready = not missing_languages and not error_message
    return {
        "installed": True,
        "ready": ready,
        "executable": executable,
        "executable_path": executable,
        "available_languages": available_languages,
        "missing_languages": missing_languages,
        "error": error_message,
    }


def _download_language_pack(language, tessdata_dir):
    destination = os.path.join(tessdata_dir, f"{language}.traineddata")
    if os.path.isfile(destination):
        return True, destination, ""

    last_error = ""
    for template in LANGUAGE_URL_TEMPLATES:
        try:
            urlretrieve(template.format(lang=language), destination)
            return True, destination, ""
        except Exception as exc:
            last_error = str(exc)
            if os.path.exists(destination):
                os.remove(destination)
    return False, destination, last_error


def _run_winget_install(package_id):
    winget_cmd = shutil.which("winget")
    if not winget_cmd:
        return False, "winget is not installed."

    command = [
        winget_cmd,
        "install",
        "--id",
        package_id,
        "--exact",
        "--accept-source-agreements",
        "--accept-package-agreements",
        "--disable-interactivity",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if result.returncode == 0:
        return True, output

    lowered_output = output.lower()
    if "already installed" in lowered_output or "no available upgrade found" in lowered_output:
        return True, output
    return False, output


def install_tesseract(required_languages=REQUIRED_OCR_LANGUAGES):
    if not sys.platform.startswith("win"):
        return {
            "ok": False,
            "status": inspect_tesseract(required_languages),
            "message": "Automatic OCR installation is supported only on Windows.",
        }

    messages = []
    executable = resolve_tesseract_cmd()
    if not executable:
        install_success = False
        for package_id in TESSERACT_PACKAGE_IDS:
            ok, output = _run_winget_install(package_id)
            if output:
                messages.append(f"{package_id}: {output}")
            if ok:
                install_success = True
                time.sleep(2)
                executable = resolve_tesseract_cmd()
                if executable:
                    break
        if not install_success or not executable:
            status = inspect_tesseract(required_languages)
            return {
                "ok": False,
                "status": status,
                "message": "\n\n".join(messages) or "Tesseract installation failed.",
            }

    configure_tesseract_cmd()
    tessdata_dir = get_tessdata_dir(executable)
    os.makedirs(tessdata_dir, exist_ok=True)

    status = inspect_tesseract(required_languages)
    download_errors = []
    for language in status["missing_languages"]:
        ok, _, error_message = _download_language_pack(language, tessdata_dir)
        if not ok:
            download_errors.append(f"{language}: {error_message}")

    final_status = inspect_tesseract(required_languages)
    if download_errors:
        messages.append("Language pack download failed: " + "; ".join(download_errors))

    return {
        "ok": final_status["ready"] and not download_errors,
        "status": final_status,
        "message": "\n\n".join(messages).strip(),
    }


def install_tesseract_with_languages(required_languages=DEFAULT_OCR_LANGUAGES):
    result = install_tesseract(required_languages)
    return {
        "success": result["ok"],
        "error": result["message"],
        "status": result["status"],
    }
