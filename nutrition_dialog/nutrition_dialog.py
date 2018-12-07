from functools import partial
import boto3
from botocore.vendored import requests
from botocore.client import Config
import json
import random
import time
import typing
import dateutil.parser
import dateutil.tz
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

# start_text = 'Скажите мне сколько и чего вы съели, а я скажу сколько это калорий. ' \
#              'Например: 300 грамм картофельного пюре и котлета. Чтобы выйти, произнесите выход'
start_text = 'Какую еду записать?'
help_text = 'Я умею считать калории. Просто скажите что Вы съели, а я скажу сколько в этом было калорий. ' \
            'Текст не должен быть слишком длинным. Желательно не более трёх блюд. Например: 300 грамм картофельного ' \
            'пюре и котлета. Чтобы выйти, скажите выход'


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


def choose_case(*, amount: float, round_to_int=False, tts_mode=False) -> str:
    if round_to_int:
        str_amount = str(int(amount))
    else:
        str_amount = str(round(amount, 2))  # Leaving only 2 digits after comma (12.03 for example)
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


@timeit
def save_session(
        *,
        session_id: str,
        event_time: datetime.datetime,
        foods_dict: dict,
        utterance: str,
        database_client) -> None:
    database_client.put_item(TableName='nutrition_sessions',
                             Item={
                                 'id': {
                                     'S': session_id,
                                 },
                                 'value': {
                                     'S': json.dumps({
                                         'time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
                                         'foods': foods_dict,
                                         'utterance': utterance}),
                                 }})


@timeit
def clear_session(
        *,
        session_id: str,
        database_client) -> None:
    database_client.delete_item(TableName='nutrition_sessions',
                                Key={
                                    'id': {
                                        'S': session_id,
                                    }, })


@timeit
def check_session(*, session_id: str, database_client) -> dict:
    result = database_client.get_item(
            TableName='nutrition_sessions', Key={'id': {'S': session_id}})
    if 'Item' not in result:
        return {}
    else:
        return json.loads(result['Item']['value']['S'])


@timeit
def get_boto3_clients(context):
    if context:
        config = Config(connect_timeout=0.5, retries={'max_attempts': 0})
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

    full_phrase_translated = full_phrase_translated.lower().replace('bisque', 'soup')

    if debug:
        print(f'Translated: {full_phrase_translated}')

    return full_phrase_translated


def russian_replacements(initial_phrase: str, tokens) -> str:
    new_phrase = initial_phrase
    replacements = [
        {'search_tokens': ['щи', 'щей'], 'search_text': [], 'replacement': 'cabbage soup'},
        {'search_tokens': ['борща', 'борщ'], 'search_text': [], 'replacement': 'vegetable soup'},
        {'search_tokens': [], 'search_text': ['биг мак', 'биг мака', 'биг маков'], 'replacement': 'big mac'},
        {'search_tokens': ['риса', 'рис'], 'search_text': [], 'replacement': 'rice'},
        {'search_tokens': ['мороженое', 'мороженого', 'мороженых'], 'search_text': [], 'replacement': 'ice cream'},
        {'search_tokens': ['кисель', 'киселя', 'киселей'], 'search_text': [], 'replacement': 'jelly'},
        {'search_tokens': ['пломбиров', 'пломбира', 'пломбир'], 'search_text': [], 'replacement': 'ice cream'},
        {'search_tokens': ['какао', ], 'search_text': [], 'replacement': 'hot chocolate'},
        {'search_tokens': ['сало', 'сала', ], 'search_text': [], 'replacement': 'fat meat'},
        {'search_tokens': ['бутылка', 'бутылки', ], 'search_text': [], 'replacement': '500 ml'},
        {'search_tokens': ['банка', 'банки', 'банок'], 'search_text': [], 'replacement': '500 ml'},
        {'search_tokens': ['ящика', 'ящиков', 'ящик'], 'search_text': [], 'replacement': '20 kg'},
        {'search_tokens': ['буханок', 'буханки', 'буханка'], 'search_text': [], 'replacement': '700 g'},
        {'search_tokens': ['батонов', 'батона', 'батон'], 'search_text': [], 'replacement': 'loaf', },
        {'search_tokens': ['пол', ], 'search_text': [], 'replacement': 'half'},
        {'search_tokens': ['раков', 'рака', 'раки', 'рак'], 'search_text': [], 'replacement': 'cray-fish'},
        {'search_tokens': ['угорь', 'угре', 'угря', 'угрей'], 'search_text': [], 'replacement': 'eel'},
        {'search_tokens': ['ведро', 'ведра', 'ведер'], 'search_text': [], 'replacement': '7 liters'},
        {'search_tokens': ['сало', 'сала', ], 'search_text': [], 'replacement': 'fat meat'},
        {'search_tokens': ['патиссонов', 'патиссона', 'патиссон', ], 'search_text': [], 'replacement': 'squash'},
        {'search_tokens': ['компота', 'компоты', 'компот'], 'search_text': [],
         'replacement': 'Stewed Apples 250 grams'},
        {'search_tokens': ['сушек', 'сушки', 'сушка', ], 'search_text': [], 'replacement': 'bagel'},
        {'search_tokens': ['рябчиков', 'рябчика', 'рябчики', 'рябчик', ], 'search_text': [], 'replacement': 'grouse'},
        {'search_tokens': ['семечек', 'семечки', ], 'search_text': [], 'replacement': 'sunflower seeds'},
        {'search_tokens': ['сникерса', 'сникерсов', 'сникерс'], 'search_text': [], 'replacement': 'Snicker'},
        {'search_tokens': ['соя', 'сои', ], 'search_text': [], 'replacement': 'soynut'},
        {'search_tokens': ['кукуруза', 'кукурузы', ], 'search_text': [], 'replacement': 'corn'},
        {'search_tokens': ['граната', 'гранат', ], 'search_text': [], 'replacement': 'pomegranate'},
        {'search_tokens': ['оливье', ], 'search_text': [], 'replacement': 'Ham Salad'},
        {'search_tokens': [], 'search_text': ['манная каша', 'манной каши', ], 'replacement': "malt o meal"},
        {'search_tokens': [], 'search_text': ['котлета из нута', 'котлет из нута', 'котлеты из нута', ],
         'replacement': '70 grams of chickpea'},
        {'search_tokens': [], 'search_text': ['котлета из капусты', 'котлет из капусты', 'котлеты из капусты',
                                              'капустная котлета', 'капустных котлет', 'капустные котлеты'],
         'replacement': '70 grams of cabbage'},
        {'search_tokens': ['желе', ], 'search_text': [], 'replacement': 'jello'},
        {'search_tokens': ['холодца', 'холодцов', 'холодец'], 'search_text': [], 'replacement': 'jelly'},
        {'search_tokens': ['лэйза', 'лейзов', 'лэйс'], 'search_text': [], 'replacement': 'lays'},
        {'search_tokens': ['кефира', 'кефир', ], 'search_text': [], 'replacement': 'kefir'},
        {'search_tokens': ['стаканов', 'стакана', 'стакан'], 'search_text': [], 'replacement': '250 ml'},
        {'search_tokens': ['бочек', 'бочки', 'бочка'], 'search_text': [], 'replacement': '208 liters'},
        {'search_tokens': [], 'search_text': ['кока кола зеро', ], 'replacement': 'Pepsi Cola Zero'},
        {'search_tokens': ['пастила', 'пастилы', 'пастил', ], 'search_text': [], 'replacement': 'зефир'},
        {'search_tokens': [], 'search_text': ['риттер спорта', 'риттер спорт', 'шоколада риттер спорта',
                                              'шоколад риттер спорт'],
         'replacement': 'ritter sport'}
        # {'search_tokens': ['тарелка', 'тарелки', 'тарелок', ], 'search_text': [], 'replacement': '400 grams'}

    ]
    for replacement in replacements:
        for text in replacement['search_text']:
            if text in initial_phrase:
                new_phrase = new_phrase.replace(text, replacement['replacement'])

        for token in replacement['search_tokens']:
            if token not in tokens:
                continue
            if token in initial_phrase:
                new_phrase = new_phrase.replace(token, replacement['replacement'])

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
                                 timeout=0.5,
                                 )
    except Exception as e:
        return {'error': str(e)}

    if response.status_code != 200:
        return {'error': response.text}

    try:
        nutrition_dict = json.loads(response.text)
        # print(nutrition_dict)
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
        response_text += f'Итого: {choose_case(amount=total_calories)}\n' \
            f'({round(total_protein, 1)} бел. ' \
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
def update_user_table(
        *,
        database_client,
        event_time: datetime.datetime,
        foods_dict: dict,
        utterance: str,
        user_id: str):
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(event_time.date())}})
    item_to_save = []
    if 'Item' in result:
        item_to_save = json.loads(result['Item']['value']['S'])
    item_to_save.append({'time': event_time.strftime('%Y-%m-%d %H:%M:%S'), 'foods': foods_dict, 'utterance': utterance})
    database_client.put_item(TableName='nutrition_users',
                             Item={
                                 'id': {
                                     'S': user_id,
                                 },
                                 'date': {'S': str(event_time.date())},
                                 'value': {
                                     'S': json.dumps(item_to_save),
                                 }})


@timeit
def what_i_have_eaten(*, date, user_id, database_client, current_timezone: str = 'UTC') -> typing.Tuple[str, float]:
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(date)}})
    if 'Item' not in result:
        return f'Не могу ничего найти за {date}', 0

    total_calories = 0
    full_text = ''
    items_list = json.loads(result['Item']['value']['S'])
    for food_number, food in enumerate(items_list, 1):
        nutrition_dict = food['foods']
        this_food_calories = 0
        food_time = dateutil.parser.parse(food['time'])
        food_time = food_time.astimezone(dateutil.tz.gettz(current_timezone))

        for f in nutrition_dict['foods']:
            calories = f.get("nf_calories", 0) or 0
            this_food_calories += calories
            total_calories += calories
        full_text += f'[{food_time.strftime("%H:%M")}] {food["utterance"]} ({this_food_calories})\n'

    full_text += f'Всего: {choose_case(amount=total_calories)}'
    return full_text, total_calories


def transform_yandex_entities_into_date(entities_tag) -> typing.Tuple[typing.Optional[datetime.date], str]:
    print(entities_tag)
    date_entities = [e for e in entities_tag if e['type'] == "YANDEX.DATETIME"]
    if len(date_entities) == 0:
        return datetime.date.today(), ''

    date_entity = date_entities[0]['value']
    date_to_return = datetime.date.today()

    if date_entity.get('year_is_relative'):
        date_to_return += dateutil.relativedelta.relativedelta(years=date_entity['year'])
    else:
        if date_entity.get('year'):
            date_to_return = date_to_return.replace(year=date_entity['year'])
    if date_entity.get('month_is_relative'):
        date_to_return += dateutil.relativedelta.relativedelta(months=date_entity['month'])
    else:
        if date_entity.get('month'):
            date_to_return = date_to_return.replace(month=date_entity['month'])
    if date_entity.get('day_is_relative'):
        date_to_return += datetime.timedelta(days=date_entity['day'])
    else:
        if date_entity.get('day'):
            date_to_return = date_to_return.replace(day=date_entity['day'])
    return date_to_return, ''


def respond_common_phrases(*, full_phrase: str, tokens: typing.List[str]) -> typing.Tuple[str, bool, bool]:
    if len(full_phrase) > 70:
        return 'Ой, текст слишком длинный. Давайте попробуем частями?', True, False

    if (
            'помощь' in tokens or
            'справка' in tokens or
            'хелп' in tokens or
            'информация' in tokens or
            'ping' in tokens or
            'пинг' in tokens or
            'умеешь' in tokens or
            ('что' in tokens and [t for t in tokens if 'делать' in t]) or
            ('как' in tokens and [t for t in tokens if 'польз' in t]) or
            'скучно' in tokens or
            'help' in tokens):
        return help_text, True, False

    if (
            'хорошо' in tokens or
            'молодец' in tokens or
            'замечательно' in tokens or
            'спасибо' in tokens or
            'отлично' in tokens
    ):
        return 'Спасибо, я стараюсь', True, False

    if (
            'привет' in tokens or
            'здравствуй' in tokens or
            'здравствуйте' in tokens
    ):
        return 'Здравствуйте. А теперь расскажите что вы съели, а скажу сколько там было калорий и ' \
               'питательных веществ.', True, False

    if (
            'выход' in tokens or
            'выйти' in tokens or
            'пока' in tokens or
            'выйди' in tokens or
            'до свидания' in tokens
    ):
        return 'До свидания', True, True

    return '', False, False


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
    full_phrase = request.get('command').lower()
    print(full_phrase)
    full_phrase_with_replacements = russian_replacements(full_phrase, tokens)

    common_response, stop_session, exit_session = respond_common_phrases(full_phrase=full_phrase, tokens=tokens)
    if exit_session:
        return construct_response_with_session(text=common_response, end_session=exit_session)
    if stop_session:
        return construct_response_with_session(text=common_response)

    if (tokens == ['да'] or tokens == ['ага'] or tokens == ['угу'] or tokens == ['конечно'] or tokens == ['ну', 'да']
            or tokens == ['давай'] or tokens == ['хорошо'] or tokens == ['можно'] or tokens == ['да', 'сохрани'] or
            tokens == ['сохрани'] or tokens == ['ну', 'сохрани'] or tokens == ['сохранить']):
        saved_session = check_session(session_id=session['session_id'], database_client=database_client)
        if not saved_session:
            return construct_response_with_session(text=make_default_text())
        update_user_table(
                database_client=database_client,
                event_time=dateutil.parser.parse(saved_session['time']),
                foods_dict=saved_session['foods'],
                user_id=session['user_id'],
                utterance=saved_session['utterance'])
        clear_session(database_client=database_client, session_id=session['session_id'])
        return construct_response_with_session(text='Сохранено. Чтобы посмотреть список сохраненной еды, '
                                                    'спросите меня что Вы ели')

    if (tokens == ['нет', ] or tokens == ['неа', ] or tokens == ['нельзя', ] or tokens == ['ну', 'нет']
            or tokens == ['не', 'надо'] or tokens == ['не', ] or tokens == ['нет', 'не', 'надо'] or
            tokens == ['да', 'нет'] or tokens == ['да', 'нет', 'наверное'] or tokens == ['не', 'сохраняй']):
        saved_session = check_session(session_id=session['session_id'], database_client=database_client)
        if not saved_session:
            return construct_response_with_session(text=make_default_text())

        clear_session(database_client=database_client, session_id=session['session_id'])
        return construct_response_with_session(text='Забыли. Чтобы посмотреть список сохраненной еды, '
                                                    'спросите меня что Вы ели')

    if 'что' in tokens and ('ел' in full_phrase or 'хран' in full_phrase):
        target_date = transform_yandex_entities_into_date(entities_tag=request.get('nlu').get('entities'))[0]
        text, total_calories = what_i_have_eaten(
                date=target_date,
                user_id=session['user_id'],
                database_client=database_client,
                current_timezone=event.get('meta').get('timezone'))
        return construct_response_with_session(
                text=text,
                tts=f'{choose_case(amount=total_calories, tts_mode=True, round_to_int=True)}')

    # searching in cache database first
    keys_dict, nutrition_dict = get_from_cache_table(request_text=full_phrase,
                                                     database_client=database_client)

    if not nutrition_dict or not context:  # if run locally, database entry is overwritten
        # translation block
        full_phrase_translated = translate(
                russian_phrase=full_phrase_with_replacements,
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
    save_session(
            session_id=session['session_id'],
            database_client=database_client,
            event_time=datetime.datetime.now(),
            foods_dict=nutrition_dict,
            utterance=full_phrase)
    write_to_cache_table(
            initial_phrase=full_phrase,
            nutrition_dict=nutrition_dict,
            database_client=database_client,
            keys_dict=keys_dict)
    return construct_response_with_session(
            text=response_text + '\nСохранить?',
            tts=f'{choose_case(amount=total_calories, tts_mode=True, round_to_int=True)}. Сохранить?')


if __name__ == '__main__':
    testing = 'что я ел вчера?'.lower()
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
            'command': testing,
            'nlu': {
                'entities': [],
                'tokens': testing.split(),
            },
            'original_utterance': testing,
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
