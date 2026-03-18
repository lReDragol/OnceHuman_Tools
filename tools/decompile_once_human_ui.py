#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class DecompileWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Once Human Decompile Tool')
        self.resize(980, 720)
        self.settings = QSettings('lReDragol', 'OnceHumanDecompileTool')
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._append_stdout)
        self.process.readyReadStandardError.connect(self._append_stderr)
        self.process.finished.connect(self._process_finished)
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        intro = QLabel(
            'Выбери папку игры Once Human, затем запусти автоматический pipeline. '
            'Инструмент создаст рядом папку decompile, распакует script.npk и при необходимости '
            'сразу вытащит mod secondary attributes.'
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        paths_group = QGroupBox('Пути')
        paths_layout = QGridLayout(paths_group)
        self.game_path_edit = QLineEdit()
        self.output_dir_edit = QLineEdit()
        self.report_path_edit = QLineEdit()
        self.mod_output_edit = QLineEdit()
        browse_button = QPushButton('Выбрать папку игры')
        browse_button.clicked.connect(self._browse_game_path)
        open_button = QPushButton('Открыть decompile')
        open_button.clicked.connect(self._open_output_dir)

        paths_layout.addWidget(QLabel('Папка игры'), 0, 0)
        paths_layout.addWidget(self.game_path_edit, 0, 1)
        paths_layout.addWidget(browse_button, 0, 2)
        paths_layout.addWidget(QLabel('Папка decompile'), 1, 0)
        paths_layout.addWidget(self.output_dir_edit, 1, 1)
        paths_layout.addWidget(open_button, 1, 2)
        paths_layout.addWidget(QLabel('Pipeline report'), 2, 0)
        paths_layout.addWidget(self.report_path_edit, 2, 1, 1, 2)
        paths_layout.addWidget(QLabel('Mod attributes JSON'), 3, 0)
        paths_layout.addWidget(self.mod_output_edit, 3, 1, 1, 2)
        layout.addWidget(paths_group)

        options_group = QGroupBox('Параметры')
        options_layout = QFormLayout(options_group)
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 64)
        self.workers_spin.setValue(1)
        self.bindict_checkbox = QCheckBox('Генерировать bindict sidecars (экспериментально)')
        self.bindict_checkbox.setChecked(False)
        self.skip_extract_checkbox = QCheckBox('Пропустить распаковку и работать по существующей decompile')
        self.extract_mod_attributes_checkbox = QCheckBox('Сразу декодировать mod secondary attributes')
        self.extract_mod_attributes_checkbox.setChecked(True)
        options_layout.addRow('Workers', self.workers_spin)
        options_layout.addRow(self.bindict_checkbox)
        options_layout.addRow(self.skip_extract_checkbox)
        options_layout.addRow(self.extract_mod_attributes_checkbox)
        layout.addWidget(options_group)

        actions_layout = QHBoxLayout()
        self.start_button = QPushButton('Запустить')
        self.start_button.clicked.connect(self._start_process)
        self.stop_button = QPushButton('Остановить')
        self.stop_button.clicked.connect(self._stop_process)
        self.stop_button.setEnabled(False)
        actions_layout.addWidget(self.start_button)
        actions_layout.addWidget(self.stop_button)
        actions_layout.addStretch(1)
        layout.addLayout(actions_layout)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit, stretch=1)

        self.game_path_edit.textChanged.connect(self._refresh_derived_paths)
        self.setCentralWidget(central)

    def _load_settings(self) -> None:
        game_path = self.settings.value('game_path', '', str)
        if game_path:
            self.game_path_edit.setText(game_path)
        workers = int(self.settings.value('workers', 1))
        self.workers_spin.setValue(max(1, workers))
        self.bindict_checkbox.setChecked(self.settings.value('bindict_sidecars', 'false') == 'true')
        self.skip_extract_checkbox.setChecked(self.settings.value('skip_extract', 'false') == 'true')
        self.extract_mod_attributes_checkbox.setChecked(self.settings.value('extract_mod_attributes', 'true') == 'true')
        self._refresh_derived_paths()

    def _save_settings(self) -> None:
        self.settings.setValue('game_path', self.game_path_edit.text().strip())
        self.settings.setValue('workers', self.workers_spin.value())
        self.settings.setValue('bindict_sidecars', 'true' if self.bindict_checkbox.isChecked() else 'false')
        self.settings.setValue('skip_extract', 'true' if self.skip_extract_checkbox.isChecked() else 'false')
        self.settings.setValue('extract_mod_attributes', 'true' if self.extract_mod_attributes_checkbox.isChecked() else 'false')

    def _refresh_derived_paths(self) -> None:
        raw_game_path = self.game_path_edit.text().strip()
        if not raw_game_path:
            self.output_dir_edit.clear()
            self.report_path_edit.clear()
            self.mod_output_edit.clear()
            return
        output_dir = Path(raw_game_path) / 'decompile'
        self.output_dir_edit.setText(str(output_dir))
        self.report_path_edit.setText(str(output_dir / 'pipeline_report.json'))
        self.mod_output_edit.setText(str(output_dir / 'mod_secondary_attributes.json'))

    def _browse_game_path(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, 'Выбери папку Once Human')
        if folder:
            self.game_path_edit.setText(folder)

    def _open_output_dir(self) -> None:
        output_dir = self.output_dir_edit.text().strip()
        if output_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))

    def _build_command(self) -> tuple[str, list[str]] | None:
        game_path = self.game_path_edit.text().strip()
        if not game_path:
            QMessageBox.warning(self, 'Нет пути', 'Сначала выбери папку игры Once Human.')
            return None
        script_path = Path(__file__).with_name('decompile_once_human.py')
        args = [
            str(script_path),
            '--game-path',
            game_path,
            '--output-dir',
            self.output_dir_edit.text().strip(),
            '--workers',
            str(self.workers_spin.value()),
            '--report-output',
            self.report_path_edit.text().strip(),
        ]
        if self.bindict_checkbox.isChecked():
            args.append('--bindict-sidecars')
        if self.skip_extract_checkbox.isChecked():
            args.append('--skip-extract')
        if self.extract_mod_attributes_checkbox.isChecked():
            args.extend(['--extract-mod-attributes', '--mod-attributes-output', self.mod_output_edit.text().strip()])
        return sys.executable, args

    def _start_process(self) -> None:
        command = self._build_command()
        if not command:
            return
        program, args = command
        self._save_settings()
        self.log_edit.clear()
        self.log_edit.appendPlainText(f'Starting: {program} {" ".join(args)}')
        self.process.start(program, args)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _stop_process(self) -> None:
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.log_edit.appendPlainText('Process terminated by user.')

    def _append_stdout(self) -> None:
        text = bytes(self.process.readAllStandardOutput()).decode('utf-8', 'ignore')
        if text:
            self.log_edit.appendPlainText(text.rstrip())

    def _append_stderr(self) -> None:
        text = bytes(self.process.readAllStandardError()).decode('utf-8', 'ignore')
        if text:
            self.log_edit.appendPlainText(text.rstrip())

    def _process_finished(self, exit_code: int) -> None:
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.log_edit.appendPlainText(f'Finished with exit code {exit_code}.')


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName('OnceHumanDecompileTool')
    window = DecompileWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
