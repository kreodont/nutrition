from functools import partial
import boto3
from botocore.vendored import requests
from botocore.client import Config
import json
import random
import time
import os


def construct_response(*,
                       text,
                       end_session=False,
                       tts=None,
                       session='',
                       message_id='',
                       user_id='',
                       verions='1.0',
                       debug=False,
                       ) -> dict:
    if tts is None:
        tts = text

    response = {
        "response": {
            "text": text,
            "tts": tts,
            "end_session": end_session
        },
        "session": {
            "session_id": session,
            "message_id": message_id,
            "user_id": user_id
        },
        "version": verions
    }

    if debug:
        print(response)

    return response


def choose_case(*, amount: float, round_to_int=False) -> str:
    if round_to_int:
        str_amount = str(int(amount))
    else:
        str_amount = str(round(amount, 2))
        if str_amount[-1] == '0':
            str_amount = str(int(amount))

    last_digit_str = str_amount[-1]
    if not round_to_int and last_digit_str != '0' and '.' in str(amount):
        return f'{str_amount} калории'
    if last_digit_str == '1':
        return f'{str_amount} калория'
    elif last_digit_str in ('2', '3', '4'):
        if len(str_amount) > 1 and str_amount[-2] == '1':
            return f'{str_amount} калорий'
        return f'{str_amount} калории'
    else:
        return f'{str_amount} калорий'


def nutrition_dialog(event: dict, context: dict) -> dict:
    """
    Parses request from yandex and returns response
    Example 1 - Normal case
    >>> nutrition_dialog({
    ...    'meta': {
    ...       'client_id': 'ru.yandex.searchplugin/7.16 (none none; android 4.4.2)',
    ...        'interfaces': {
    ...            'screen': {},
    ...        },
    ...        'locale': 'ru-RU',
    ...        'timezone': 'UTC',
    ...    },
    ...    'request': {
    ...        'command': '300 грамм картофельного пюре и котлета и стакан яблочного сока',
    ...        'nlu': {
    ...            'entities': [],
    ...            'tokens': ['ghb'],
    ...        },
    ...        'original_utterance': '300 грамм картофельного пюре и котлета и стакан яблочного сока',
    ...        'type': 'SimpleUtterance',
    ...    },
    ...    'session':
    ...        {
    ...            'message_id': 1,
    ...            'new': False,
    ...            'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6',
    ...            'skill_id': '5799f33a-f13b-459f-b7ff-3039666f2b8b',
    ...            'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E',
    ...        },
    ...    'version': '1.0',
    ... },
    ...        {})
    {'response': {'text': '1. 339 калорий\\n2. 270.6 калорий\\n3. 114.1 калории\\nИтого: 723.7 калории',
    'tts': '1. 339 калорий\\n2. 270.6 калорий\\n3. 114.1 калории\\nИтого: 723.7 калории',
    'end_session': False},
    'session': {'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6', 'message_id': 1, 'user_id':
    '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E'},
    'version': '1.0'}


    :param event:
    :param context:
    :return:
    """

    def make_default_text():
        return random.choice(default_texts) + '. Например: ' + random.choice(example_food_texts) + '. ' + \
               random.choice(exit_texts) + '.'

    start_time = time.time()

    event.setdefault('debug', bool(context))
    debug = event.get('debug')
    if debug:
        print(event)

    default_texts = ['Это не похоже на название еды. Попробуйте сформулировать иначе',
                     'Хм. Не могу понять что это. Попробуйте сказать иначе',
                     'Такой еды я пока не знаю. Попробуйте сказать иначе'
                     ]

    exit_texts = ['Чтобы выйти, произнесите выход']

    example_food_texts = ['Бочка варенья и коробка печенья',
                          'Литр молока и килограмм селедки',
                          '2 куска пиццы с ананасом',
                          '200 грамм брокколи и 100 грамм шпината',
                          'ананас и рябчик',
                          '2 блина со сгущенкой',
                          'тарелка риса, котлета и стакан апельсинового сока',
                          'банан, апельсин и манго',
                          'черная икра, красная икра, баклажанная икра',
                          'каша из топора и свежевыжатый березовый сок',
                          ]

    request = event.get('request')
    if not request:
        return construct_response(text='Неверный запрос, нет поля request')

    session = event.get('session')  # type: dict
    if not session:
        return construct_response(text='Неверный запрос, нет поля session')

    construct_response_with_session = partial(construct_response,
                                              session=session['session_id'],
                                              user_id=session['user_id'],
                                              message_id=session.get('message_id'),
                                              debug=debug,
                                              )

    is_new_session = session.get('new')
    start_text = 'Скажите мне сколько и чего вы съели, а я скажу сколько это калорий. ' \
                 'Например: 300 грамм картофельного пюре и котлета. Чтобы выйти, произнесите выход'
    help_text = 'Я умею считать калории. Просто скажите что Вы съели, а я скажу сколько в этом было калорий. ' \
                'Текст не должен быть слишком длинным. Желательно не более трёх блюд. Чтобы выйти, скажите выход'

    config = Config(connect_timeout=0.8, retries={'max_attempts': 0})
    if context:
        translation_client = boto3.client('translate', config=config)
    else:
        translation_client = boto3.Session(profile_name='kreodont').client('translate')

    if is_new_session:
        return construct_response_with_session(text=start_text)

    tokens = request.get('nlu').get('tokens')  # type: list

    if ('помощь' in tokens or
            'справка' in tokens or
            'хелп' in tokens or
            'информация' in tokens or
            'ping' in tokens or
            'пинг' in tokens or
            request.get('original_utterance').endswith('?') or
            'умеешь' in tokens or
            ('что' in tokens and [t for t in tokens if 'дел' in t]) or
            ('как' in tokens and [t for t in tokens if 'польз' in t]) or
            'скучно' in tokens or
            'help' in tokens):
        return construct_response_with_session(text=help_text)

    if (
            'хорошо' in tokens or
            'молодец' in tokens):
        return construct_response_with_session(text='Спасибо, я стараюсь')

    if (
            'привет' in tokens or
            'здравствуй' in tokens or
            'здравствуйте' in tokens):
        return construct_response_with_session(text='Здравствуйте. А теперь расскажите что вы съели, '
                                                    'а скажу сколько там было калорий и питательных веществ.')

    if ('выход' in tokens or
            'выйти' in tokens or
            'пока' in tokens or
            'выйди' in tokens or
            'до свидания' in tokens):
        return construct_response_with_session(text='До свидания', end_session=True)

    full_phrase = request.get('original_utterance')
    if len(full_phrase) > 70:
        return construct_response_with_session(text='Ой, текст слишком длинный. Давайте попробуем частями?')

    try:
        full_phrase_translated = translation_client.translate_text(Text=full_phrase,
                                                                   SourceLanguageCode='ru',
                                                                   TargetLanguageCode='en'
                                                                   ).get('TranslatedText')  # type:str
    except requests.exceptions.ReadTimeout:
        return construct_response_with_session(text=make_default_text())

    full_phrase_translated = full_phrase_translated. \
        replace('acne', 'eel'). \
        replace('drying', 'bagel'). \
        replace('mopper', 'grouse')

    if debug:
        print(f'Translated: {full_phrase_translated}')

    x_app_id = os.environ['NUTRITIONIXID']
    x_app_key = os.environ['NUTRITIONIXKEY']

    request_data = {'line_delimited': False,
                    'query': full_phrase_translated,
                    'timezone': "Europe/Moscow",
                    'use_branded_foods': False,
                    'use_raw_foods': False,
                    }

    try:
        response = requests.post('https://trackapi.nutritionix.com/v2/natural/nutrients',
                                 data=json.dumps(request_data),
                                 headers={'content-type': 'application/json',
                                          'x-app-id': x_app_id,
                                          'x-app-key': x_app_key},
                                 timeout=0.6,
                                 )
    except Exception as e:
        if debug:
            print(e)
        return construct_response_with_session(text=make_default_text())

    if response.status_code != 200:
        print(f'Exception: {response.text}')
        return construct_response_with_session(text=make_default_text())

    nutrionix_dict = json.loads(response.text)

    if 'foods' not in nutrionix_dict or not nutrionix_dict['foods']:
        if debug:
            print(f'Tag foods not found or empty')
        return construct_response_with_session(text=make_default_text())

    if debug:
        print(nutrionix_dict)

    response_text = ''  # type: str
    total_calories = 0.0  # type: float
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

    for number, food_name in enumerate(nutrionix_dict['foods']):
        calories = nutrionix_dict["foods"][number].get("nf_calories", 0) or 0
        total_calories += calories
        protein = nutrionix_dict["foods"][number].get("nf_protein", 0) or 0
        total_protein += protein
        fat = nutrionix_dict["foods"][number].get("nf_total_fat", 0) or 0
        total_fat += fat
        carbohydrates = nutrionix_dict["foods"][number].get("nf_total_carbohydrate", 0) or 0
        total_carbohydrates += carbohydrates
        sugar = nutrionix_dict["foods"][number].get("nf_sugars", 0) or 0
        total_sugar += sugar
        number_string = ''
        if len(nutrionix_dict["foods"]) > 1:
            number_string = f'{number + 1}. '
        response_text += f'{number_string}{choose_case(amount=calories)}\n' \
            f'({round(protein, 1)} бел. ' \
            f'{round(fat, 1)} жир. ' \
            f'{round(carbohydrates, 1)} угл. ' \
            f'{round(sugar, 1)} сах.)\n'

    if len(nutrionix_dict["foods"]) > 1:
        response_text += f'Итого: {choose_case(amount=total_calories)}\n({round(total_protein, 1)} бел. ' \
            f'{round(total_fat, 1)} жир. ' \
            f'{round(total_carbohydrates, 1)} угл. {round(total_sugar, 1)} сах.)'

    if debug:
        end_time = time.time()
        print(f'{(end_time - start_time) * 1000} ms')
        print(response_text)

    return construct_response_with_session(text=response_text, tts=f'Итого: {choose_case(amount=total_calories)}')


if __name__ == '__main__':
    nutrition_dialog({
        'meta': {
            'client_id': 'ru.yandex.searchplugin/7.16 (none none; android 4.4.2)',
            'interfaces': {
                'screen': {},
            },
            'locale': 'ru-RU',
            'timezone': 'UTC',
        },
        'request': {
            'command': '300 грамм картофельного пюре и котлета и стакан яблочного сока',
            'nlu': {
                'entities': [],
                'tokens': ['ghb'],
            },
            'original_utterance': '300 грамм картофельного пюре и котлета и стакан яблочного сока',
            'type': 'SimpleUtterance',
        },
        'session':
            {
                'message_id': 1,
                'new': False,
                'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6',
                'skill_id': '5799f33a-f13b-459f-b7ff-3039666f2b8b',
                'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E',
            },
        'version': '1.0',
        'debug': True,
    },
            {})
    # import doctest
    # doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE, verbose=False)
