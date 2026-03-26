#!/usr/bin/env python3
"""
Скрипт для массового исправления кодировки MP3-тэгов.

Проблема: Тэги сохранены в кодировке LATIN1, но содержат данные в Windows-1251.
Решение: Перечитать байты как Windows-1251 и сохранить в UTF-8.
"""

__version__ = "0.1.0"

import os
import sys
from pathlib import Path
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.mp3 import MP3


def fix_encoding(filepath, dry_run=False, verbose=True):
    """
    Исправляет кодировку тэгов в MP3-файле.
    
    Args:
        filepath: Путь к MP3-файлу
        dry_run: Если True, не записывать изменения (только показать)
        verbose: Выводить подробную информацию
    
    Returns:
        bool: True если изменения были сделаны (или будут в dry_run)
    """
    if verbose:
        print(f"\n{'='*60}")
        print(f"Файл: {os.path.basename(filepath)}")
        print(f"{'='*60}")
    
    try:
        audio = MP3(filepath)
        
        if not audio.tags:
            if verbose:
                print("  Нет тэгов, пропускаем.")
            return False
        
        tags = audio.tags
        modified = False
        
        # Список текстовых фреймов для исправления
        text_frames = [
            'TALB',  # Альбом
            'TIT1',  # Заголовок
            'TIT2',  # Название трека
            'TPE1',  # Артист
            'TPE2',  # Альбом артист
            'TPE3',  # Дирижёр
            'TPE4',  # Ремиксер
            'TCOM',  # Композитор
            'TCON',  # Жанр
            'TLAN',  # Язык
            'TDRC',  # Год
            'TRCK',  # Номер трека
            'TPOS',  # Номер диска
            'TPUB',  # Лейбл
            'TSRC',  # ISRC
            'USLT',  # Текст песни
            'COMM',  # Комментарии
        ]
        
        for frame_id in text_frames:
            if frame_id not in tags:
                continue
                
            frame = tags[frame_id]
            
            # Проверяем текущую кодировку
            current_encoding = getattr(frame, 'encoding', None)
            
            if current_encoding is None:
                continue
            
            # Если кодировка уже UTF-8 или UTF-16, пропускаем
            from mutagen.id3 import Encoding
            if current_encoding in (Encoding.UTF8, Encoding.UTF16):
                if verbose:
                    print(f"  {frame_id}: кодировка {current_encoding} — OK")
                continue
            
            # Если LATIN1 — пытаемся исправить
            if current_encoding == Encoding.LATIN1:
                if hasattr(frame, 'text') and frame.text:
                    # Получаем сырые байты и декодируем как Windows-1251
                    fixed_text = []
                    for text in frame.text:
                        if isinstance(text, str):
                            # Кодируем обратно в байты как latin1, затем декодируем как cp1251
                            try:
                                raw_bytes = text.encode('latin-1')
                                fixed = raw_bytes.decode('windows-1251')
                                fixed_text.append(fixed)
                                if verbose:
                                    print(f"  {frame_id}: {repr(text)} → {fixed}")
                                modified = True
                            except (UnicodeEncodeError, UnicodeDecodeError) as e:
                                if verbose:
                                    print(f"  {frame_id}: ошибка конвертации — {e}")
                                fixed_text.append(text)
                        else:
                            fixed_text.append(text)
                    
                    if modified:
                        frame.text = fixed_text
                        frame.encoding = Encoding.UTF8
        
        if modified:
            if dry_run:
                print(f"  [DRY RUN] Будет сохранено с исправленной кодировкой")
            else:
                tags.save(filepath)
                print(f"  ✓ Тэги исправлены и сохранены")
        else:
            if verbose:
                print("  Тэги не требуют исправления")
        
        return modified
        
    except ID3NoHeaderError:
        if verbose:
            print("  Нет ID3-тэгов")
        return False
    except Exception as e:
        print(f"  Ошибка: {e}")
        return False


def process_directory(directory, recursive=True, dry_run=False):
    """
    Обрабатывает все MP3-файлы в директории.
    
    Args:
        directory: Путь к директории
        recursive: Обрабатывать рекурсивно
        dry_run: Только показать, что будет сделано
    """
    directory = Path(directory)
    
    if not directory.exists():
        print(f"Директория не найдена: {directory}")
        return
    
    pattern = "**/*.mp3" if recursive else "*.mp3"
    mp3_files = list(directory.glob(pattern))
    
    if not mp3_files:
        print(f"MP3-файлы не найдены в {directory}")
        return
    
    print(f"Найдено MP3-файлов: {len(mp3_files)}")
    if dry_run:
        print("РЕЖИМ ПРОСМОТРА (без записи)")
    
    fixed_count = 0
    for filepath in mp3_files:
        if fix_encoding(str(filepath), dry_run=dry_run):
            fixed_count += 1
    
    print(f"\n{'='*60}")
    print(f"Всего файлов: {len(mp3_files)}")
    print(f"Исправлено: {fixed_count}")
    if dry_run:
        print(f"Для применения исправлений запустите без флага --dry-run")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Исправление кодировки MP3-тэгов (LATIN1 → UTF-8)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Примеры:\n'
               '  python fix_mp3_tags.py . -r           # Исправить текущую папку рекурсивно\n'
               '  python fix_mp3_tags.py --dry-run      # Показать, что будет исправлено\n'
               '  python fix_mp3_tags.py файл.mp3       # Исправить один файл\n'
    )
    parser.add_argument(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Путь к файлу или директории (по умолчанию: текущая папка)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Только показать изменения, не записывать'
    )
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Рекурсивно обрабатывать поддиректории'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if path.is_file():
        fix_encoding(str(path), dry_run=args.dry_run)
    elif path.is_dir():
        process_directory(path, recursive=args.recursive, dry_run=args.dry_run)
    else:
        print(f"Путь не найден: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
