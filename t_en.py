import re
import sys
import concurrent.futures
from deep_translator import GoogleTranslator

# Конфигурация: только английский
TARGET_LANG = "English"
TARGET_CODE = "en"
OUTPUT_FILE = "addon_english.txt"
INPUT_FILE = "addon_russian.txt"

# Регулярка для захвата строки KV (ключ - значение)
KV_PATTERN = re.compile(r'^(\s*"[^"]+"\s*")([^"\\]*(?:\\.[^"\\]*)*)(".*)$')

# УЛУЧШЕННАЯ ЗАЩИТА ТЕГОВ И СИМВОЛОВ
# <[^>]+>      -> Любые HTML теги (<font color="...">, <br>, </font>)
# \\[nrt"]     -> Экранированные символы (\n, \", \t, \r)
# %[\w\.]+%?   -> Переменные со знаком процента (%damage%, %s, %%)
# {[^}]+}      -> Переменные в фигурных скобках
TAG_PATTERN = re.compile(r'(<[^>]+>|\\[nrt"]|%[\w\.]+%?|%%|%\w+|{[^}]+})')

def protect_and_translate(text, translator):
    if not text.strip() or text.isnumeric():
        return text

    # Сохраняем начальные и конечные пробелы
    leading_spaces = len(text) - len(text.lstrip(' '))
    trailing_spaces = len(text) - len(text.rstrip(' '))
    clean_text = text.strip()

    # Заменяем теги и спецсимволы на временные маркеры
    placeholders = []
    def repl(match):
        placeholders.append(match.group(0))
        return f" __TAG{len(placeholders)-1}__ "

    protected_text = TAG_PATTERN.sub(repl, clean_text)
    
    # Переводим текст с маркерами
    try:
        translated_text = translator.translate(protected_text)
    except Exception as e:
        # В случае ошибки API возвращаем оригинал
        return text

    # === АНТИ-КАВЫЧКИ (КРИТИЧЕСКАЯ ЗАЩИТА) ===
    # Гугл переводчик часто превращает русские «» в английские "
    # Так как правильные \" сейчас спрятаны в __TAG__, любые оставшиеся " - это смерть для файла.
    # Заменяем их на красивые и безопасные « »
    if '"' in translated_text:
        parts = translated_text.split('"')
        safe_text = ""
        for i, part in enumerate(parts[:-1]):
            # Четные индексы закрываем открывающей кавычкой, нечетные - закрывающей
            safe_text += part + ('«' if i % 2 == 0 else '»')
        translated_text = safe_text + parts[-1]
        
    # Восстанавливаем теги (используем IGNORECASE, так как гугл может перевести в __tag0__)
    for i, tag in enumerate(placeholders):
        # Защищаем обратные слеши в тегах при подстановке через лямбду
        translated_text = re.sub(
            fr'\s*__TAG{i}__\s*', 
            lambda _, t=tag: t, 
            translated_text, 
            count=1, 
            flags=re.IGNORECASE
        )
        
    # Возвращаем пробелы по краям
    return (' ' * leading_spaces) + translated_text.strip() + (' ' * trailing_spaces)

def process_line(index, line):
    """Функция для обработки одной строки в отдельном потоке"""
    # Меняем заголовок языка
    if '"Language"' in line and '"Russian"' in line:
        return index, line.replace('"Russian"', f'"{TARGET_LANG}"')

    match = KV_PATTERN.match(line)
    if match:
        prefix = match.group(1)
        original_value = match.group(2)
        suffix = match.group(3)
        
        # Если в строке есть буквы (есть что переводить)
        if any(c.isalpha() for c in original_value):
            translator = GoogleTranslator(source='ru', target=TARGET_CODE)
            translated_value = protect_and_translate(original_value, translator)
            return index, f"{prefix}{translated_value}{suffix}\n"
            
    # Если это просто скобка, пустая строка или ключ без текста
    return index, line

def main():
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Файл {INPUT_FILE} не найден!")
        return

    print(f"\n--- Начало быстрого перевода на {TARGET_LANG} ({TARGET_CODE}) ---")
    
    # Подготавливаем массив для результата (чтобы сохранить оригинальный порядок строк)
    out_lines = [None] * len(lines)
    
    # Используем ThreadPoolExecutor для МНОГОПОТОЧНОСТИ (Ускоряет в 15-20 раз)
    max_threads = 20
    completed = 0
    total = len(lines)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        # Запускаем все строки в пуле потоков
        futures = {executor.submit(process_line, i, line): i for i, line in enumerate(lines)}
        
        for future in concurrent.futures.as_completed(futures):
            index, translated_line = future.result()
            out_lines[index] = translated_line
            
            completed += 1
            # Красивый прогресс-бар
            sys.stdout.write(f"\rПереведено строк: {completed}/{total} ({(completed/total)*100:.1f}%)")
            sys.stdout.flush()

    # Сохраняем в новый файл
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)
        
    print(f"\n\nГотово! Супер-быстрый перевод завершен и сохранен в {OUTPUT_FILE}")

if __name__ == '__main__':
    main()