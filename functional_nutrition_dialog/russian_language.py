def choose_case(*, amount: float, round_to_int=False, tts_mode=False) -> str:
    if round_to_int:
        str_amount = str(int(amount))
    else:
        # Leaving only 2 digits after comma (12.03 for example)
        str_amount = str(round(amount, 2))
        if int(amount) == amount:
            str_amount = str(int(amount))

    last_digit_str = str_amount[-1]

    if not round_to_int and '.' in str_amount:  # 12.04 калории
        return f'{str_amount} калории'
    # below amount is integer for sure
    if last_digit_str == '1':  # 21 калория (20 одна калория in tts mode)
        if len(str_amount) > 1 and str_amount[-2] == '1':  # 11 калорий
            return f'{str_amount} калорий'
        if tts_mode:
            if len(str_amount) > 1:
                first_part = str(int(str_amount[:-1]) * 10)
            else:
                first_part = ''
            str_amount = f'{first_part} одна'
        return f'{str_amount} калория'
    elif last_digit_str in ('2', '3', '4'):
        if len(str_amount) > 1 and str_amount[-2] == '1':  # 11 калорий
            return f'{str_amount} калорий'
        if tts_mode:
            if len(str_amount) > 1:
                first_part = str(int(str_amount[:-1]) * 10)
            else:
                first_part = ''
            if last_digit_str == '2':
                str_amount = f'{first_part} две'
        return f'{str_amount} калории'  # 22 калории
    else:
        return f'{str_amount} калорий'  # 35 калорий
