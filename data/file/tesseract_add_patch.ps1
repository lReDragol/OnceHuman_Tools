# Скрипт для добавления Tesseract в PATH

$TesseractPath = "C:\Program Files\Tesseract-OCR"

# Получаем текущие значения PATH
$oldPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)

# Проверяем, есть ли уже Tesseract в PATH
if ($oldPath -notlike "*$TesseractPath*") {
    # Добавляем путь к Tesseract в PATH
    $newPath = $oldPath + ";" + $TesseractPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::Machine)

    Write-Host "Путь к Tesseract успешно добавлен в PATH. Перезапустите командную строку."
} else {
    Write-Host "Путь к Tesseract уже существует в PATH."
}
