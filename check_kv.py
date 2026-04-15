import re

# Регулярка для пары "Ключ" "Значение" (с поддержкой правильных \" внутри)
KV_PATTERN = re.compile(r'^\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s+"([^"\\]*(?:\\.[^"\\]*)*)"\s*(?://.*)?$')

# Регулярка для одиночных ключей-заголовков (например, "Language" или "Tokens")
SECTION_PATTERN = re.compile(r'^\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*(?://.*)?$')

def check_file(filename):
    errors = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                clean_line = line.strip()
                
                # Игнорируем пустые строки, комментарии и фигурные скобки
                if not clean_line or clean_line.startswith('//') or clean_line in ('{', '}'):
                    continue
                
                # Проверяем, является ли строка идеальной парой "Ключ" "Значение"
                if KV_PATTERN.match(line):
                    continue
                    
                # Проверяем, является ли строка валидным заголовком (например, "Tokens")
                if SECTION_PATTERN.match(line):
                    continue
                
                # Если скрипт дошел сюда — строка сломана. Пытаемся понять причину:
                # Временно убираем правильные экранированные кавычки \", чтобы посчитать "плохие"
                clean_for_count = line.replace('\\"', '')
                quotes_count = clean_for_count.count('"')
                
                reason = "Нарушена структура (пропущен пробел, лишние символы вне кавычек и т.д.)"
                
                if quotes_count % 2 != 0:
                    reason = f"Нечетное количество кавычек ({quotes_count}). Забыта открывающая или закрывающая кавычка."
                elif quotes_count > 4:
                    reason = f"Слишком много кавычек ({quotes_count}). Внутри текста есть обычные кавычки вместо экранированных (нужно \\\")."
                elif quotes_count < 4 and quotes_count != 2:
                    reason = "Недостаточно кавычек для ключа и значения."
                elif '""' in clean_line:
                    reason = "Двойные кавычки слиплись (возможно, пропущен пробел между ключом и значением)."

                errors.append((i, reason, clean_line))

    except FileNotFoundError:
        print(f"Файл {filename} не найден!")
        return

    if errors:
        print(f"❌ Найдено сломанных строк: {len(errors)}\n")
        for line_num, reason, content in errors:
            print(f"Строка {line_num} | {reason}")
            print(f"Текст:  {content}\n")
        print("💡 Как исправить:")
        print("1. Убедитесь, что строка выглядит так: \"Ключ\" \"Значение\"")
        print("2. Если внутри значения нужны кавычки, перед ними должен стоять слеш: \"Она сказала \\\"Привет\\\"\"")
    else:
        print("✅ Ошибок не найдено! Структура кавычек в файле идеальна.")

if __name__ == '__main__':
    check_file('addon_russian.txt')