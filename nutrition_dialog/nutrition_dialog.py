from functools import partial
import boto3
from botocore.vendored import requests
from botocore.client import Config
import json
import random
import time
import typing
import dateutil.parser
import datetime

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

start_text = 'Скажите мне сколько и чего вы съели, а я скажу сколько это калорий. ' \
             'Например: 300 грамм картофельного пюре и котлета. Чтобы выйти, произнесите выход'
help_text = 'Я умею считать калории. Просто скажите что Вы съели, а я скажу сколько в этом было калорий. ' \
            'Текст не должен быть слишком длинным. Желательно не более трёх блюд. Чтобы выйти, скажите выход'


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


def timeit(target_function):
    def timed(*args, **kwargs):
        start_time = time.time()
        result = target_function(*args, **kwargs)
        end_time = time.time()
        milliseconds = (end_time - start_time) * 1000
        if milliseconds > 300 or target_function.__name__ != 'nutrition_dialog':  # not to print ping timing
            print(f'Function "{target_function.__name__}" time: {milliseconds} ms')

        return result

    return timed


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


@timeit
def get_from_cache_table(*, request_text: str, database_client) -> typing.Tuple[dict, dict]:
    keys_dict = {}
    food_dict = {}
    items = database_client.batch_get_item(
            RequestItems={
                'nutrition_cache': {
                    'Keys': [
                        {
                            'initial_phrase': {
                                'S': '_key'},
                        },
                        {
                            'initial_phrase': {
                                'S': request_text},
                        }
                    ]}})
    for item in items['Responses']['nutrition_cache']:
        if item['initial_phrase']['S'] == '_key':
            keys_dict = json.loads(item['response']['S'])
        if item['initial_phrase']['S'] == request_text:
            print()
            food_dict = json.loads(item['response']['S'])

    return keys_dict, food_dict


@timeit
def write_to_cache_table(*, initial_phrase: str, nutrition_dict: dict, database_client, keys_dict: dict) -> None:
    database_client.put_item(TableName='nutrition_cache',
                             Item={
                                 'initial_phrase': {
                                     'S': initial_phrase,
                                 },
                                 'response': {
                                     'S': json.dumps(nutrition_dict),
                                 }})
    database_client.put_item(TableName='nutrition_cache',
                             Item={
                                 'initial_phrase': {
                                     'S': '_key',
                                 },
                                 'response': {
                                     'S': json.dumps(keys_dict),
                                 }})


def get_boto3_clients(context):
    if context:
        config = Config(connect_timeout=0.8, retries={'max_attempts': 0})
        translation_client = boto3.client('translate', config=config)
        database_client = boto3.client('dynamodb', config=config)
    else:
        translation_client = boto3.Session(profile_name='kreodont').client('translate')
        database_client = boto3.Session(profile_name='kreodont').client('dynamodb')

    return translation_client, database_client


def search_common_phrases(tokens, request, construct_response_with_session):
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


@timeit
def translate(*, russian_phrase, translation_client, debug):
    try:
        full_phrase_translated = translation_client.translate_text(Text=russian_phrase,
                                                                   SourceLanguageCode='ru',
                                                                   TargetLanguageCode='en'
                                                                   ).get('TranslatedText')  # type:str
    except requests.exceptions.ReadTimeout:
        return 'timeout'

    full_phrase_translated = full_phrase_translated.lower(). \
        replace('acne', 'eel'). \
        replace('drying', 'bagel'). \
        replace('mopper', 'grouse'). \
        replace('seeds', 'sunflower seeds'). \
        replace('fat', 'fat meat'). \
        replace('grenade', 'pomegranate'). \
        replace('olivier', 'Ham Salad'). \
        replace('borsch', 'vegetable soup'). \
        replace('schi', 'cabbage soup').\
        replace('semolina porridge', 'semolina cake').\
        replace('chickpea cutlets', 'chickpea 70 grams').\
        replace('chickpea cutlet', 'chickpea 70 grams').\
        replace('snikers', 'Snicker').\
        replace('compote', 'Stewed Apples 250 grams').\
        replace('bottle', '500 ml').\
        replace('cabbage cutlet', 'cabbage 70 grams').\
        replace('bucket', '7 liters')

    if debug:
        print(f'Translated: {full_phrase_translated}')

    return full_phrase_translated


def russian_replacements(initial_phrase: str, tokens) -> str:
    new_phrase = initial_phrase.replace('щи', 'капустный суп').\
        replace('биг мак', 'big mac').\
        replace('какао', 'hot chocolate 300 grams')
    if 'рис' in tokens:
        new_phrase = new_phrase.replace('рис', 'rice')
    return new_phrase


def make_default_text():
    return random.choice(default_texts) + '. Например: ' + random.choice(example_food_texts) + '. ' + \
           random.choice(exit_texts) + '.'


@timeit
def query_endpoint(*, link, login, password, phrase) -> dict:
    try:
        response = requests.post(link,
                                 data=json.dumps({'query': phrase}),
                                 headers={'content-type': 'application/json',
                                          'x-app-id': login,
                                          'x-app-key': password},
                                 timeout=0.6,
                                 )
    except Exception as e:
        return {'error': str(e)}

    if response.status_code != 200:
        return {'error': response.text}

    try:
        nutrition_dict = json.loads(response.text)
    except Exception as e:
        return {'error': f'Cannot parse result json: "{response.text}". Exception: {e}'}

    if 'foods' not in nutrition_dict or not nutrition_dict['foods']:
        return {'error': f'Tag foods not found or empty: {nutrition_dict}'}

    return nutrition_dict


def make_final_text(*, nutrition_dict) -> typing.Tuple[str, float]:
    response_text = ''  # type: str
    total_calories = 0.0  # type: float
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

    for number, food_name in enumerate(nutrition_dict['foods']):
        calories = nutrition_dict["foods"][number].get("nf_calories", 0) or 0
        total_calories += calories
        weight = nutrition_dict['foods'][number].get('serving_weight_grams', 0) or 0
        protein = nutrition_dict["foods"][number].get("nf_protein", 0) or 0
        total_protein += protein
        fat = nutrition_dict["foods"][number].get("nf_total_fat", 0) or 0
        total_fat += fat
        carbohydrates = nutrition_dict["foods"][number].get("nf_total_carbohydrate", 0) or 0
        total_carbohydrates += carbohydrates
        sugar = nutrition_dict["foods"][number].get("nf_sugars", 0) or 0
        total_sugar += sugar
        number_string = ''
        if len(nutrition_dict["foods"]) > 1:
            number_string = f'{number + 1}. '
        response_text += f'{number_string}{choose_case(amount=calories)} в {weight} гр.\n' \
            f'({round(protein, 1)} бел. ' \
            f'{round(fat, 1)} жир. ' \
            f'{round(carbohydrates, 1)} угл. ' \
            f'{round(sugar, 1)} сах.)\n'

    if len(nutrition_dict["foods"]) > 1:
        response_text += f'Итого: {choose_case(amount=total_calories)}\n({round(total_protein, 1)} бел. ' \
            f'{round(total_fat, 1)} жир. ' \
            f'{round(total_carbohydrates, 1)} угл. {round(total_sugar, 1)} сах.)'

    return response_text, total_calories


def choose_key(keys_dict):
    min_usage_value = float('inf')
    min_usage_key = None
    for k in keys_dict['keys']:
        # deleting keys usages if they are older than 24 hours
        k['dates'] = [d for d in k['dates'] if
                      dateutil.parser.parse(d) > datetime.datetime.now() - datetime.timedelta(hours=24)]
        if min_usage_key is None:
            min_usage_key = k
        if min_usage_value > len(k['dates']):
            min_usage_key = k
            min_usage_value = len(k['dates'])

    min_usage_key['dates'].append(str(datetime.datetime.now()))
    return min_usage_key['name'], min_usage_key['pass'], keys_dict


@timeit
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
    300 грамм картофельного пюре и котлета и стакан яблочного сока
    {'response': {'text': '1. 339 калорий\\n(5.9 бел. 12.6 жир. 50.8 угл.
    4.2 сах.)\\n2. 270.59 калории\\n(30.6 бел. 8.4 жир. 15.8 угл. 0.9 сах.)\\n3. 114.08
    калории\\n(0.2 бел. 0.3 жир. 28.0 угл. 23.9 сах.)\\nИтого:
    723.67 калории\\n(36.7 бел. 21.4 жир. 94.7 угл. 29.0 сах.)', 'tts': 'Итого: 723.67 калории',
    'end_session': False}, 'session': {'session_id': 'f12a4adc-ca1988d-1978333d-3ffd2ca6', 'message_id': 1,
    'user_id': '574027C0C2A1FEA0E65694182E19C8AB69A56FC404B938928EF74415CF05137E'}, 'version': '1.0'}

    """

    event.setdefault('debug', bool(context))
    debug = event.get('debug')
    if debug:
        print(event)

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

    # clients initialization must be before any checks to warm-up lambda function
    translation_client, database_client = get_boto3_clients(context)

    if is_new_session:
        return construct_response_with_session(text=start_text)

    tokens = request.get('nlu').get('tokens')  # type: list
    full_phrase = request.get('original_utterance').lower()
    full_phrase = russian_replacements(full_phrase, tokens)

    if len(full_phrase) > 70:
        return construct_response_with_session(text='Ой, текст слишком длинный. Давайте попробуем частями?')

    search_common_phrases(tokens, request, construct_response_with_session)

    # searching in cache database first
    keys_dict, nutrition_dict = get_from_cache_table(request_text=full_phrase,
                                                     database_client=database_client)

    if not nutrition_dict or not context:  # if run locally, database entry is overwritten
        # translation block
        full_phrase_translated = translate(
                russian_phrase=full_phrase,
                translation_client=translation_client,
                debug=debug)

        if full_phrase_translated == 'timeout':
            return construct_response_with_session(text=make_default_text())
        # End of translation block

        login, password, keys_dict = choose_key(keys_dict)

        nutrition_dict = query_endpoint(
                link=keys_dict['link'],
                login=login,
                password=password,
                phrase=full_phrase_translated,
        )
        if 'error' in nutrition_dict:
            print(nutrition_dict['error'])
            return construct_response_with_session(text=make_default_text())

    response_text, total_calories = make_final_text(nutrition_dict=nutrition_dict)

    write_to_cache_table(
            initial_phrase=full_phrase,
            nutrition_dict=nutrition_dict,
            database_client=database_client,
            keys_dict=keys_dict)
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
            'command': '...',
            'nlu': {
                'entities': [],
                'tokens': ['ghb'],
            },
            'original_utterance': 'ведро воды',
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
