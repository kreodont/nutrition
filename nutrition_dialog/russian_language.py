from yandex_types import YandexRequest
from dataclasses import replace


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


def russian_replacements_in_original_utterance(
        *,
        yandex_request: YandexRequest) -> YandexRequest:
    phrase = yandex_request.original_utterance
    tokens = yandex_request.tokens
    replacements = [
        {'search_tokens': ['щи', 'щей'], 'search_text': [],
         'replacement': 'cabbage soup'},
        {'search_tokens': ['борща', 'борщ'], 'search_text': [],
         'replacement': 'vegetable soup'},
        {'search_tokens': ['рассольника', 'рассольники', 'рассольников',
                           'рассольник'],
         'search_text': [], 'replacement': 'vegetable soup'},
        {'search_tokens': [],
         'search_text': ['биг мак', 'биг мака', 'биг маков'],
         'replacement': 'big mac'},
        {'search_tokens': [],
         'search_text': ['селедка под шубой', 'селедки под шубой',
                         'селедок под шубой',
                         'сельдь под шубой', 'сельди под шубой',
                         'сельдей под шубой', ],
         'replacement': 'Dressed Herring'},
        {'search_tokens': ['риса', 'рис'], 'search_text': [],
         'replacement': 'rice'},
        {'search_tokens': ['мороженое', 'мороженого', 'мороженых', 'эскимо'],
         'search_text': [],
         'replacement': 'ice cream'},
        {'search_tokens': ['кисель', 'киселя', 'киселей'], 'search_text': [],
         'replacement': 'jelly'},
        {'search_tokens': ['сырники', 'сырника', 'сырников', 'сырник',
                           'сырниками'], 'search_text': [],
         'replacement': 'cottage chese'},
        {'search_tokens': ['пломбиров', 'пломбира', 'пломбир'],
         'search_text': [], 'replacement': 'ice cream'},
        {'search_tokens': ['какао', ], 'search_text': [],
         'replacement': 'hot chocolate'},
        {'search_tokens': ['сало', 'сала', ], 'search_text': [],
         'replacement': 'fat meat'},
        {'search_tokens': ['бутылка', 'бутылки', ], 'search_text': [],
         'replacement': '500 ml'},
        {'search_tokens': ['банка', 'банки', 'банок'], 'search_text': [],
         'replacement': '500 ml'},
        {'search_tokens': ['ящика', 'ящиков', 'ящик'], 'search_text': [],
         'replacement': '20 kg'},
        {'search_tokens': ['буханок', 'буханки', 'буханка'], 'search_text': [],
         'replacement': '700 g'},
        {'search_tokens': ['батонов', 'батона', 'батон'], 'search_text': [],
         'replacement': 'loaf', },
        {'search_tokens': ['пол', ], 'search_text': [], 'replacement': 'half'},
        {'search_tokens': ['раков', 'рака', 'раки', 'рак'], 'search_text': [],
         'replacement': 'cray-fish'},
        {'search_tokens': ['панкейка', 'панкейков', 'панкейк', 'панкейки'],
         'search_text': [], 'replacement': 'pancake'},
        {'search_tokens': ['угорь', 'угре', 'угря', 'угрей'], 'search_text': [],
         'replacement': 'eel'},
        {'search_tokens': ['ведро', 'ведра', 'ведер'], 'search_text': [],
         'replacement': '7 liters'},
        {'search_tokens': ['сало', 'сала', ], 'search_text': [],
         'replacement': 'fat meat'},
        {'search_tokens': ['патиссонов', 'патиссона', 'патиссон', ],
         'search_text': [], 'replacement': 'squash'},
        {'search_tokens': ['компота', 'компоты', 'компот'], 'search_text': [],
         'replacement': 'Stewed Apples 250 grams'},
        {'search_tokens': ['сушек', 'сушки', 'сушка', ], 'search_text': [],
         'replacement': 'bagel'},
        {'search_tokens': ['винегрета', 'винегретом', 'винегретов', 'винегрет',
                           'винегреты', ], 'search_text': [],
         'replacement': 'vegetable salad'},
        {'search_tokens': ['рябчиков', 'рябчика', 'рябчики', 'рябчик', ],
         'search_text': [], 'replacement': 'grouse'},
        {'search_tokens': ['семечек', 'семечки', ], 'search_text': [],
         'replacement': 'sunflower seeds'},
        {'search_tokens': ['сникерса', 'сникерсов', 'сникерс'],
         'search_text': [], 'replacement': 'Snicker'},
        {'search_tokens': ['соя', 'сои', ], 'search_text': [],
         'replacement': 'soynut'},
        {'search_tokens': ['кукуруза', 'кукурузы', ], 'search_text': [],
         'replacement': 'corn'},
        {'search_tokens': ['яйца', 'яиц', ], 'search_text': [],
         'replacement': 'eggs'},
        {'search_tokens': ['граната', 'гранат', ], 'search_text': [],
         'replacement': 'pomegranate'},
        {'search_tokens': ['голубец', 'голубцы', 'голубца', 'голубцов'],
         'search_text': [],
         'replacement': 'cabbage roll'},
        {'search_tokens': ['оливье', ], 'search_text': [],
         'replacement': 'Ham Salad'},
        {'search_tokens': [], 'search_text': ['салат оливье'],
         'replacement': 'Ham Salad'},
        {'search_tokens': [], 'search_text': ['манная каша', 'манной каши', ],
         'replacement': "malt o meal"},
        {'search_tokens': [],
         'search_text': ['пшенная каша', 'пшенной каши', 'пшенной каши'],
         'replacement': "malt o meal"},
        {'search_tokens': [],
         'search_text': ['котлета из нута', 'котлет из нута',
                         'котлеты из нута', ],
         'replacement': '70 grams of chickpea'},
        {'search_tokens': [],
         'search_text': ['котлета из капусты', 'котлет из капусты',
                         'котлеты из капусты',
                         'капустная котлета', 'капустных котлет',
                         'капустные котлеты'],
         'replacement': '70 grams of cabbage'},
        {'search_tokens': ['желе', ], 'search_text': [],
         'replacement': 'jello'},
        {'search_tokens': ['холодца', 'холодцов', 'холодец'], 'search_text': [],
         'replacement': 'jelly'},
        {'search_tokens': ['лэйза', 'лейзов', 'лэйс'], 'search_text': [],
         'replacement': 'lays'},
        {'search_tokens': ['кефира', 'кефир', ], 'search_text': [],
         'replacement': 'kefir'},
        {'search_tokens': ['стаканов', 'стакана', 'стакан'], 'search_text': [],
         'replacement': '250 ml'},
        {'search_tokens': ['бочек', 'бочки', 'бочка'], 'search_text': [],
         'replacement': '208 liters'},
        {'search_tokens': [], 'search_text': ['кока кола зеро', ],
         'replacement': 'Pepsi Cola Zero'},
        {'search_tokens': ['пастила', 'пастилы', 'пастил', ], 'search_text': [],
         'replacement': 'зефир'},
        {'search_tokens': ['халва', 'халвы', 'халв', ], 'search_text': [],
         'replacement': 'halvah'},
        {'search_tokens': ['творога', 'творогом', 'творогов', 'творог'],
         'search_text': [], 'replacement':
             'cottage cheese'},
        {'search_tokens': ['конфета', 'конфеты', 'конфетами', 'конфетой',
                           'конфет'], 'search_text': [], 'replacement':
             'candy'},
        {'search_tokens': ['миллиграммами', 'миллиграмма', 'миллиграмм',
                           'миллиграммом'], 'search_text': [],
         'replacement': '0 g '},
        {'search_tokens': ['обезжиренного', 'обезжиренным', 'обезжиренных',
                           'обезжиренный'], 'search_text': [],
         'replacement': 'nonfat'},
        {'search_tokens': ['пюрешка', 'пюрешки', 'пюрешкой', ],
         'search_text': [], 'replacement': 'mashed potato'},
        {'search_tokens': ['соленый', 'соленая', 'соленого', 'соленой',
                           'соленым', 'соленом', 'соленое', 'солеными',
                           'соленых'], 'search_text': [], 'replacement': ''},
        {'search_tokens': [],
         'search_text': ['макароны карбонара', 'макарон карбонара',
                         'вермишель карбонара',
                         'вермишели карбонара', 'паста карбонара',
                         'пасты карбонара'],
         'replacement': 'Carbonara'},
        {'search_tokens': [],
         'search_text': ['кукурузная каша', 'кукурузные каши',
                         'кукурузной каши',
                         'каша кукурузная', 'каши кукурузные',
                         'каши кукурузной'],
         'replacement': 'grits'},
        {'search_tokens': [],
         'search_text': ['картофель по-деревенски', 'картофель по деревенски',
                         'картофеля по-деревенски', 'картофеля по деревенски',
                         'картофелей по-деревенски',
                         'картофелей по-деревенски', ],
         'replacement': 'Roast Potato'},
        {'search_tokens': [], 'search_text': ['риттер спорта', 'риттер спорт',
                                              'шоколада риттер спорта',
                                              'шоколад риттер спорт'],
         'replacement': 'ritter sport'},
        {'search_tokens': ['морсом', 'морсов', 'морса', 'морсы', 'морс', ],
         'search_text': [],
         'replacement': 'Cranberry Drink'},
        {'search_tokens': ['вареники', 'вареников', 'варениками', 'вареника',
                           'вареник', ], 'search_text': [],
         'replacement': 'Veggie Dumplings'},
        {'search_tokens': ['плова', 'пловов', 'пловы', 'плов'],
         'search_text': [],
         'replacement': 'Rice Pilaf'},
        {'search_tokens': ['сырков', 'сырка', 'сырки', 'сырок'],
         'search_text': [],
         'replacement': 'Cream Cheese'}
    ]
    for replacement in replacements:
        for text in replacement['search_text']:
            if text in phrase:
                phrase = phrase.replace(text, replacement['replacement'])

        for token in replacement['search_tokens']:
            if token not in tokens:
                continue
            if token in phrase:
                phrase = phrase.replace(token, replacement['replacement'])

    return replace(yandex_request, original_utterance=phrase)
