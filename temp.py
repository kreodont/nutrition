def make_text_to_speech_number(text: str) -> str:
    if '.' in text:
        return text
    previous_digits = ''
    if len(text) > 1:
        previous_digits = str(int(text[:-1]) * 10)
    last_digits = text[-1]
    if last_digits == 0:
        last_text = ''
    elif last_digits == '1':
        last_text = 'одна'
    elif last_digits == '2':
        last_text = 'две'
    else:
        last_text = last_digits
    return previous_digits + " " + last_text


print(make_text_to_speech_number('1331001'))