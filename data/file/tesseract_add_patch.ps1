# ������ ��� ���������� Tesseract � PATH

$TesseractPath = "C:\Program Files\Tesseract-OCR"

# �������� ������� �������� PATH
$oldPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)

# ���������, ���� �� ��� Tesseract � PATH
if ($oldPath -notlike "*$TesseractPath*") {
    # ��������� ���� � Tesseract � PATH
    $newPath = $oldPath + ";" + $TesseractPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::Machine)

    Write-Host "���� � Tesseract ������� �������� � PATH. ������������� ��������� ������."
} else {
    Write-Host "���� � Tesseract ��� ���������� � PATH."
}
