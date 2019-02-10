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
import re

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

start_text = 'Какую еду записать?'
help_text = 'Я считаю калории. Просто скажите что вы съели, а я скажу сколько в этом было калорий. Например: соевое ' \
            'молоко с хлебом. Потом я спрошу ' \
            'надо ли сохранить этот прием пищи, и если вы скажете да, я запишу его в свою базу данных. ' \
            'Можно сказать не ' \
            'просто да, а указать время приема пищи, например: да, вчера в 9 часов 30 минут. После того, как прием ' \
            'пищи сохранен, вы сможете узнать свое суточное потребление калорий с помощью команды "что я ел(а)?". ' \
            'При этом также можно указать время, например: "Что я ел вчера?" или "Что я ела неделю назад?". Если ' \
            'какая-то еда была внесена ошибочно, можно сказать "Удалить соевое молоко с хлебом". ' \
            'Прием пищи "Соевое молоко с хлебом" будет удален'


def construct_response(*,
                       text,
                       end_session=False,
                       tts=None,
                       session='',
                       message_id='',
                       user_id='',
                       verions='1.0',
                       debug=False,
                       has_screen=True,
                       with_button=False
                       ) -> dict:
    if tts is None or not has_screen:  # for devices without screen we need to pronounce everything
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
    if with_button and has_screen:
        response["response"]['text'] += '\nКстати, если у вас закончились продукты, ' \
                                        'воспользуйтесь навыком Вторая память, чтобы не забыть, какие'
        response["response"]['buttons'] = [{
            "title": "Вторая память",
            "payload": {},
            "url": "https://dialogs.yandex.ru/store/skills/00203e6e-vtoraya-pamya",
            "hide": False
        }]

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
    full_phrase_translated = re.sub(r'without (\w+)', '', full_phrase_translated)

    if debug:
        print(f'Translated: {full_phrase_translated}')

    return full_phrase_translated


def russian_replacements(initial_phrase: str, tokens) -> str:
    new_phrase = initial_phrase
    replacements = [
        {'search_tokens': ['щи', 'щей'], 'search_text': [], 'replacement': 'cabbage soup'},
        {'search_tokens': ['борща', 'борщ'], 'search_text': [], 'replacement': 'vegetable soup'},
        {'search_tokens': ['рассольника', 'рассольники', 'рассольников', 'рассольник'],
         'search_text': [], 'replacement': 'vegetable soup'},
        {'search_tokens': [], 'search_text': ['биг мак', 'биг мака', 'биг маков'], 'replacement': 'big mac'},
        {'search_tokens': [], 'search_text': ['селедка под шубой', 'селедки под шубой', 'селедок под шубой',
                                              'сельдь под шубой', 'сельди под шубой', 'сельдей под шубой', ],
         'replacement': 'Dressed Herring'},
        {'search_tokens': ['риса', 'рис'], 'search_text': [], 'replacement': 'rice'},
        {'search_tokens': ['мороженое', 'мороженого', 'мороженых', 'эскимо'], 'search_text': [],
         'replacement': 'ice cream'},
        {'search_tokens': ['кисель', 'киселя', 'киселей'], 'search_text': [], 'replacement': 'jelly'},
        {'search_tokens': ['сырники', 'сырника', 'сырников', 'сырник', 'сырниками'], 'search_text': [],
         'replacement': 'cottage chese'},
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
        {'search_tokens': ['панкейка', 'панкейков', 'панкейк', 'панкейки'],
         'search_text': [], 'replacement': 'pancake'},
        {'search_tokens': ['угорь', 'угре', 'угря', 'угрей'], 'search_text': [], 'replacement': 'eel'},
        {'search_tokens': ['ведро', 'ведра', 'ведер'], 'search_text': [], 'replacement': '7 liters'},
        {'search_tokens': ['сало', 'сала', ], 'search_text': [], 'replacement': 'fat meat'},
        {'search_tokens': ['патиссонов', 'патиссона', 'патиссон', ], 'search_text': [], 'replacement': 'squash'},
        {'search_tokens': ['компота', 'компоты', 'компот'], 'search_text': [],
         'replacement': 'Stewed Apples 250 grams'},
        {'search_tokens': ['сушек', 'сушки', 'сушка', ], 'search_text': [], 'replacement': 'bagel'},
        {'search_tokens': ['винегрета', 'винегретом', 'винегретов', 'винегрет', 'винегреты', ], 'search_text': [],
         'replacement': 'vegetable salad'},
        {'search_tokens': ['рябчиков', 'рябчика', 'рябчики', 'рябчик', ], 'search_text': [], 'replacement': 'grouse'},
        {'search_tokens': ['семечек', 'семечки', ], 'search_text': [], 'replacement': 'sunflower seeds'},
        {'search_tokens': ['сникерса', 'сникерсов', 'сникерс'], 'search_text': [], 'replacement': 'Snicker'},
        {'search_tokens': ['соя', 'сои', ], 'search_text': [], 'replacement': 'soynut'},
        {'search_tokens': ['кукуруза', 'кукурузы', ], 'search_text': [], 'replacement': 'corn'},
        {'search_tokens': ['яйца', 'яиц', ], 'search_text': [], 'replacement': 'eggs'},
        {'search_tokens': ['граната', 'гранат', ], 'search_text': [], 'replacement': 'pomegranate'},
        {'search_tokens': ['голубец', 'голубцы', 'голубца', 'голубцов'], 'search_text': [],
         'replacement': 'cabbage roll'},
        {'search_tokens': ['оливье', ], 'search_text': [], 'replacement': 'Ham Salad'},
        {'search_tokens': [], 'search_text': ['салат оливье'], 'replacement': 'Ham Salad'},
        {'search_tokens': [], 'search_text': ['манная каша', 'манной каши', ], 'replacement': "malt o meal"},
        {'search_tokens': [], 'search_text': ['пшенная каша', 'пшенной каши', 'пшенной каши'],
         'replacement': "malt o meal"},
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
        {'search_tokens': ['халва', 'халвы', 'халв', ], 'search_text': [], 'replacement': 'halvah'},
        {'search_tokens': ['творога', 'творогом', 'творогов', 'творог'], 'search_text': [], 'replacement':
            'cottage cheese'},
        {'search_tokens': ['конфета', 'конфеты', 'конфетами', 'конфетой', 'конфет'], 'search_text': [], 'replacement':
            'candy'},
        {'search_tokens': ['миллиграммами', 'миллиграмма', 'миллиграмм', 'миллиграммом'], 'search_text': [],
         'replacement': '0 g '},
        {'search_tokens': ['обезжиренного', 'обезжиренным', 'обезжиренных', 'обезжиренный'], 'search_text': [],
         'replacement': 'nonfat'},
        {'search_tokens': ['пюрешка', 'пюрешки', 'пюрешкой', ], 'search_text': [], 'replacement': 'mashed potato'},
        {'search_tokens': ['соленый', 'соленая', 'соленого', 'соленой', 'соленым', 'соленом', 'соленое', 'солеными',
                           'соленых'], 'search_text': [], 'replacement': ''},
        {'search_tokens': [], 'search_text': ['макароны карбонара', 'макарон карбонара', 'вермишель карбонара',
                                              'вермишели карбонара', 'паста карбонара', 'пасты карбонара'],
         'replacement': 'Carbonara'},
        {'search_tokens': [], 'search_text': ['кукурузная каша', 'кукурузные каши', 'кукурузной каши',
                                              'каша кукурузная', 'каши кукурузные', 'каши кукурузной'],
         'replacement': 'grits'},
        {'search_tokens': [], 'search_text': ['картофель по-деревенски', 'картофель по деревенски',
                                              'картофеля по-деревенски', 'картофеля по деревенски',
                                              'картофелей по-деревенски', 'картофелей по-деревенски', ],
         'replacement': 'Roast Potato'},
        {'search_tokens': [], 'search_text': ['риттер спорта', 'риттер спорт', 'шоколада риттер спорта',
                                              'шоколад риттер спорт'],
         'replacement': 'ritter sport'},
        {'search_tokens': ['морсом', 'морсов', 'морса', 'морсы', 'морс', ], 'search_text': [],
         'replacement': 'Cranberry Drink'},
        {'search_tokens': ['вареники', 'вареников', 'варениками', 'вареника', 'вареник', ], 'search_text': [],
         'replacement': 'Veggie Dumplings'},
        {'search_tokens': ['плова', 'пловов', 'пловы', 'плов'], 'search_text': [],
         'replacement': 'Rice Pilaf'},
        {'search_tokens': ['сырков', 'сырка', 'сырки', 'сырок'], 'search_text': [],
         'replacement': 'Cream Cheese'}
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
        response_text += f'Итого: ({round(total_protein, 1)} бел. ' \
            f'{round(total_fat, 1)} жир. ' \
            f'{round(total_carbohydrates, 1)} угл. {round(total_sugar, 1)} сах.' \
            f')\n_\n{choose_case(amount=total_calories)}\n_\n'

    return response_text, total_calories


def choose_key(keys_dict):
    min_usage_value = 90000
    min_usage_key = None
    limit_date = str(datetime.datetime.now() - datetime.timedelta(hours=24))
    for k in keys_dict['keys']:
        # deleting keys usages if they are older than 24 hours
        k['dates'] = [d for d in k['dates'] if d > limit_date]
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
        return f'Не могу ничего найти за {date}. Чтобы еда сохранялась в мою базу, не забывайте говорить ' \
                   f'"Сохранить", после того, как я посчитаю калории.', 0

    total_calories = 0
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

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
            protein = f.get("nf_protein", 0) or 0
            total_protein += protein
            fat = f.get("nf_total_fat", 0) or 0
            total_fat += fat
            carbohydrates = f.get("nf_total_carbohydrate", 0) or 0
            total_carbohydrates += carbohydrates
            sugar = f.get("nf_sugars", 0) or 0
            total_sugar += sugar
        full_text += f'[{food_time.strftime("%H:%M")}] {food["utterance"]} ({round(this_food_calories, 2)})\n'

    all_total = total_protein + total_fat + total_carbohydrates
    if all_total == 0:
        return f'Не могу ничего найти за {date}. Я сохраняю еду в свою базу, только если вы скажете ' \
                   f'Сохранить после того, как я спрошу.', 0
    percent_protein = round((total_protein / all_total) * 100)
    percent_fat = round((total_fat / all_total) * 100)
    percent_carbohydrates = round((total_carbohydrates / all_total) * 100)
    full_text += f'\nВсего: \n{round(total_protein)} ({percent_protein}%) ' \
        f'бел. {round(total_fat)} ({percent_fat}%) жир. {round(total_carbohydrates)} ({percent_carbohydrates}%) ' \
        f'угл. {round(total_sugar)} сах.\n_\n{choose_case(amount=round(total_calories, 2))}'
    return full_text, total_calories


def transform_yandex_entities_into_dates(entities_tag) -> typing.List[dict]:
    """
    Takes entities tag and returns list of [date, note, (start, end)]
    :param entities_tag:
    :return:
    """
    date_entities = [e for e in entities_tag if e['type'] == "YANDEX.DATETIME"]
    if len(date_entities) == 0:
        return []

    dates = []
    for d in date_entities:
        date_entity = d['value']
        date_to_return = datetime.datetime.now()
        start_token = d['tokens']['start']
        end_token = d['tokens']['end']

        if 'year_is_relative' in date_entity and date_entity['year_is_relative']:
            date_to_return += dateutil.relativedelta.relativedelta(years=date_entity['year'])
        else:
            if 'year' in date_entity:
                date_to_return = date_to_return.replace(year=date_entity['year'])
        if 'month_is_relative' in date_entity and date_entity['month_is_relative']:
            date_to_return += dateutil.relativedelta.relativedelta(months=date_entity['month'])
        else:
            if 'month' in date_entity:
                date_to_return = date_to_return.replace(month=date_entity['month'])
        if 'day_is_relative' in date_entity and date_entity['day_is_relative']:
            date_to_return += datetime.timedelta(days=date_entity['day'])
        else:
            if 'day' in date_entity:
                date_to_return = date_to_return.replace(day=date_entity['day'])
        if 'hour_is_relative' in date_entity and date_entity['hour_is_relative']:
            date_to_return += datetime.timedelta(minutes=date_entity['hour'] * 60)
        else:
            if 'hour' in date_entity:
                date_to_return = date_to_return.replace(hour=date_entity['hour'])
        if 'minute_is_relative' in date_entity and date_entity['minute_is_relative']:
            date_to_return += datetime.timedelta(minutes=date_entity['minute'])
        else:
            if 'minute' in date_entity:
                date_to_return = date_to_return.replace(minute=date_entity['minute'])
        dates.append({'datetime': date_to_return, 'notes': '', 'start': start_token, 'end': end_token})

    return dates


def respond_common_phrases(*, full_phrase: str, tokens: typing.List[str]) -> typing.Tuple[str, bool, bool]:
    if len(full_phrase) > 70 and 'удалить' not in full_phrase:
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
            ('что' in tokens and [t for t in tokens if 'умеешь' in t]) or
            ('как' in tokens and [t for t in tokens if 'польз' in t]) or
            'скучно' in tokens or
            'help' in tokens):
        return help_text, True, False

    if (
            tokens == ['спасибо', ] or
            tokens == ['молодец', ] or
            tokens == ['спасибо', ] or
            tokens == ['отлично', ] or
            tokens == ['хорошо', ] or
            tokens == ['окей', ] or full_phrase in (
            'ты классная',
            'классная штука',
            'классно',
            'ты молодец',
            'круто',
            'обалдеть',
            'прикольно',
            'клево',)
    ):
        return 'Спасибо, я стараюсь', True, False

    if (
            'привет' in tokens or
            'здравствуй' in tokens or
            'здравствуйте' in tokens
    ):
        return 'Здравствуйте. А теперь расскажите что вы съели, а я скажу сколько там было калорий и ' \
               'питательных веществ.', True, False

    if (
            'выход' in tokens or
            'выйти' in tokens or
            'пока' in tokens or
            'выйди' in tokens or
            'до свидания' in full_phrase.lower() or
            'всего доброго' in full_phrase.lower() or
            tokens == ['алиса', ] or
            full_phrase in ('иди на хуй', 'стоп')

    ):
        return 'До свидания', True, True

    return '', False, False


def delete_food(*,
                database_client,
                date: datetime.date,
                utterance_to_delete: str,
                user_id: str) -> str:
    result = database_client.get_item(
            TableName='nutrition_users',
            Key={'id': {'S': user_id}, 'date': {'S': str(date)}})

    if 'Item' not in result:
        return f'Никакой еды не найдено за {date}. Чтобы еда появилась в моей базе, необходимо не ' \
            f'забывать говорить "сохранить"'

    items = json.loads(result['Item']['value']['S'])
    items_to_delete = []
    for item in items:
        if item['utterance'] and utterance_to_delete.strip() == item['utterance'].replace(',', '').strip():
            items_to_delete.append(item)
    if not items_to_delete:
        return f'"{utterance_to_delete}" не найдено за {date}. Найдено: {[i["utterance"] for i in items]}. Чтобы ' \
            f'удалить еду, нужно произнести Удалить "еда" именно в том виде, как она записана. ' \
            f'Например, удалить {items[0]["utterance"]}'
    elif len(items_to_delete) > 1:
        return f'Несколько значений подходят: {[i["utterance"] for i in items_to_delete]}. Уточните, какое удалить?'
    items.remove(items_to_delete[0])
    database_client.put_item(TableName='nutrition_users',
                             Item={
                                 'id': {
                                     'S': user_id,
                                 },
                                 'date': {'S': str(date)},
                                 'value': {
                                     'S': json.dumps(items),
                                 }})
    return f'"{utterance_to_delete}" удалено'


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

    has_screen = event.get('meta').get('interfaces').get('screen')
    if has_screen == {}:
        has_screen = True
    else:
        has_screen = False
    construct_response_with_session = partial(construct_response,
                                              session=session['session_id'],
                                              user_id=session['user_id'],
                                              message_id=session.get('message_id'),
                                              debug=debug,
                                              has_screen=has_screen
                                              )

    is_new_session = session.get('new')

    # clients initialization must be before any checks to warm-up lambda function
    t1 = time.time()
    translation_client, database_client = get_boto3_clients(context)
    boto3_fetching_time = time.time() - t1

    if is_new_session:
        return construct_response_with_session(text=start_text)

    tokens = request.get('nlu').get('tokens')  # type: list
    full_phrase = str(request.get('command')).lower().strip()
    print(full_phrase)
    full_phrase_with_replacements = russian_replacements(full_phrase, tokens)

    common_response, stop_session, exit_session = respond_common_phrases(full_phrase=full_phrase, tokens=tokens)
    if exit_session:
        return construct_response_with_session(text=common_response, end_session=exit_session)
    if stop_session:
        if 'Я считаю калории' in common_response:
            return construct_response(session=session['session_id'],
                                      user_id=session['user_id'],
                                      message_id=session.get('message_id'),
                                      debug=debug,
                                      has_screen=has_screen,
                                      text=common_response,
                                      end_session=exit_session, with_button=True)
        return construct_response_with_session(text=common_response)

    if 'удалить' in tokens or 'удали' in tokens or 'убери' in tokens or 'убрать' in tokens:
        cleaned_tokens = [t for t in tokens if t not in ('удалить', 'еду', 'удали', 'убери', 'убрать')]
        if not cleaned_tokens:
            return construct_response_with_session(text='Скажите название еды, которую надо удалить. Например: '
                                                        '"Удалить пюре с котлетой"')

        found_dates = transform_yandex_entities_into_dates(entities_tag=request.get('nlu').get('entities'))
        if not found_dates:
            target_date = datetime.date.today()
            food_to_search = ' '.join(cleaned_tokens)
            return construct_response_with_session(text=delete_food(
                    database_client=database_client,
                    date=target_date,
                    utterance_to_delete=food_to_search,
                    user_id=session['user_id']))
        else:
            target_date = found_dates[0]['datetime'].date()
            date_tokens = tokens[found_dates[0]['start']:found_dates[0]['end']]
            print(f'Tokens: {tokens}')
            print(f'Start: {found_dates[0]["start"]} End: {found_dates[0]["start"]}')
            print(date_tokens)
            cleaned_tokens = [t for t in cleaned_tokens if t not in date_tokens]
            return construct_response_with_session(text=delete_food(
                    database_client=database_client,
                    date=target_date,
                    utterance_to_delete=' '.join(cleaned_tokens),
                    user_id=session['user_id']))

    if [t for t in tokens if 'человеч' in t] or tokens == ['мясо', 'человека'] or full_phrase in ('человек',):
        return construct_response_with_session(text='Доктор Лектер, это вы?')

    if full_phrase in ('кошка', 'кошку', 'кот', 'кота', 'котенок', 'котенка'):
        return construct_response_with_session(text='Неешь, подумой')

    if full_phrase in ('говно', 'какашка', 'кака', 'дерьмо', 'фекалии', 'какахе', 'какахи'):
        return construct_response_with_session(text='Вы имели в виду "Сладкий хлеб"?')

    if full_phrase in ('это много', 'это мало', 'что-то много', 'что-то мало', 'так много '):
        return construct_response_with_session(text='Если вы нашли ошибку, напишите моему разработчику, '
                                                    'и он объяснит мне, как правильно')

    if full_phrase == 'хуй' or full_phrase == 'моржовый хуй':
        return construct_response_with_session(text='С солью или без соли?')

    if full_phrase in ('никакую', 'ничего'):
        return construct_response_with_session(text='Хорошо, дайте знать, когда что-то появится')

    if full_phrase in ('заткнись', 'замолчи', 'молчи', 'молчать'):
        return construct_response_with_session(text='Молчу')

    if full_phrase in ('как тебя зовут', ):
        return construct_response_with_session(text='Я умный счетчик калорий, а имя мне пока не придумали. '
                                                    'Может, Вы придумаете?')

    if full_phrase in ('умный счетчик калорий',):
        return construct_response_with_session(text='Да, я здесь')

    if full_phrase in ('а где сохраняются', 'где сохраняются', 'где сохранить', 'а зачем сохранять', 'зачем сохранять'):
        return construct_response_with_session(text='Приемы пищи сохраняются в моей базе данных. Ваши приемы '
                                                    'пищи будут доступны только Вам. Я могу быть Вашим личным '
                                                    'дневником калорий')

    if full_phrase in ('дура', 'дурочка', 'иди на хер', 'пошла нахер', 'тупица',
                       'идиотка', 'тупорылая', 'тупая'):
        return construct_response_with_session(text='Все мы можем ошибаться. Напишите моему разработчику, '
                                                    'а он меня накажет и научит больше не ошибаться.')

    if full_phrase in ('норма калорий',
                       'сколько я набрала калорий',
                       'сколько я набрал калорий',
                       'сколько в день нужно калорий',
                       'сколько нужно съесть калорий в день',
                       'дневная норма калорий',

                       ) or 'норма потребления калорий' in full_phrase:
        return construct_response_with_session(text='Этого я пока не умею, но планирую скоро научиться. '
                                                    'Следите за обновлениями')

    if 'запусти навык' in full_phrase:
        return construct_response_with_session(text='Я навык Умный Счетчик Калорий. Чтобы вернуться в Алису и '
                                                    'запустить другой навык, скажите Выход')

    if (tokens == ['да'] or tokens == ['ага'] or tokens == ['угу'] or tokens == ['конечно'] or tokens == ['ну', 'да']
            or tokens == ['давай'] or tokens == ['хорошо'] or tokens == ['можно'] or tokens == ['да', 'сохрани'] or
            tokens == ['сохрани'] or tokens == ['ну', 'сохрани'] or tokens == ['сохранить'] or
            tokens == ['да', 'сохранит'] or tokens == ['да', 'сохранить'] or tokens == ['да', 'да'] or
            tokens == ['да', 'спасибо'] or full_phrase in (
                    'да да сохрани',
                    'да да да',
                    'хранить',
                    'да конечно',
                    'ну давай',
                    'сохраняй',
                    'сохранить да',
                    'давай да',
                    'сохранять',
            )):
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
                                                    'спросите "Что я ел сегодня?"', tts='Сохранено')

    if (tokens == ['нет', ] or tokens == ['неа', ] or tokens == ['нельзя', ] or tokens == ['ну', 'нет']
        or tokens == ['не', 'надо'] or tokens == ['не', ] or tokens == ['нет', 'не', 'надо'] or
        tokens == ['да', 'нет'] or tokens == ['да', 'нет', 'наверное'] or tokens == ['не', 'сохраняй']
        or tokens == ['нет', 'спасибо']) or \
            full_phrase in (
            'не надо сохранять',
            'нет не сохранить',
            'нет не сохраняй',
            'не нужно сохранять',
            'нет нет',
            'нет не сохраняет',
            'не надо спасибо',
            'не надо',
            'нет не надо',
            'нет не нужно',
    ):
        saved_session = check_session(session_id=session['session_id'], database_client=database_client)
        if not saved_session:
            return construct_response_with_session(text=make_default_text())

        clear_session(database_client=database_client, session_id=session['session_id'])
        return construct_response_with_session(text='Забыли. Чтобы посмотреть список сохраненной еды, '
                                                    'спросите меня что Вы ели', tts='Забыли')

    # checking if we want to save for specific day
    dates_in_tokens = transform_yandex_entities_into_dates(entities_tag=request.get('nlu').get('entities'))
    if (dates_in_tokens and len(dates_in_tokens) == 1 and dates_in_tokens[0]['start'] == 0 and
            dates_in_tokens[0]['end'] == len(tokens)):  # if all there is date in tokens and all the tokens is date
        saved_session = check_session(session_id=session['session_id'], database_client=database_client)
        if not saved_session:
            return construct_response_with_session(text=make_default_text())
        update_user_table(
                database_client=database_client,
                event_time=dates_in_tokens[0]['datetime'].replace(
                        tzinfo=dateutil.tz.gettz(
                                event.get('meta').get('timezone'))
                ).astimezone(dateutil.tz.gettz('UTC')),
                foods_dict=saved_session['foods'],
                user_id=session['user_id'],
                utterance=saved_session['utterance'])
        clear_session(database_client=database_client, session_id=session['session_id'])
        return construct_response_with_session(
                text=f'Сохранено за {dates_in_tokens[0]["datetime"].date()}. Чтобы посмотреть список сохраненной еды, '
                f'спросите меня что Вы ели', tts='Сохранено')

    if (('что' in tokens or 'сколько' in tokens) and ('ел' in full_phrase or 'хран' in full_phrase)) or \
            full_phrase in ('покажи результат',
                            'открыть список сохранения',
                            'скажи результат',
                            'общий результат',
                            'общий итог',
                            'какой итог',
                            'сколько всего',
                            'сколько калорий',
                            'какой результат',
                            'сколько в общем калорий',
                            'сколько всего калорий',
                            'сколько калорий в общей сумме',
                            'сколько я съел калорий',
                            'сколько я съела калорий',
                            'покажи сохраненную',
                            'покажи сколько калорий',
                            'сколько я съел',
                            'сколько всего калорий было',
                            'сколько всего калорий было в день',
                            'список сохраненные еды',
                            'список сохраненной еды',
                            'общая сумма калорий за день',
                            'посчитай все калории за сегодня',
                            'сколько все вместе за весь день',
                            'ну посчитай сколько всего калорий',
                            'посчитай сколько всего калорий',
                            'подсчитать калории',
                            'сколько калорий у меня сегодня',
                            'подсчитать все',
                            'сколько всего получилось',
                            'сколько за день',
                            'сколько калорий за день',
                            'сколько сегодня калорий',
                            'сколько было сегодня калорий',
                            'сколько сегодня калорий было'
                            ):
        found_dates = transform_yandex_entities_into_dates(entities_tag=request.get('nlu').get('entities'))
        if not found_dates:
            target_date = datetime.date.today()
        else:
            target_date = found_dates[0]['datetime'].date()
        text, total_calories = what_i_have_eaten(
                date=target_date,
                user_id=session['user_id'],
                database_client=database_client,
                current_timezone=event.get('meta').get('timezone'))
        return construct_response_with_session(
                text=text,
                tts=f'{choose_case(amount=total_calories, tts_mode=True, round_to_int=True)}')

    # searching in cache database first
    try:
        keys_dict, nutrition_dict = get_from_cache_table(request_text=full_phrase,
                                                         database_client=database_client)
    except Exception as e:
        print(e)
        return construct_response_with_session(text=make_default_text())

    if 'error' in nutrition_dict and context:
        return construct_response_with_session(text=make_default_text())

    # If cursors retreive time is big, there probably won't be enough time to fetch API, so returning default
    if context and boto3_fetching_time > 0.3:
        return construct_response_with_session(text=make_default_text())

    if not nutrition_dict or not context:  # if run locally, database entry is overwritten
        # translation block
        t1 = time.time()
        full_phrase_translated = translate(
                russian_phrase=full_phrase_with_replacements,
                translation_client=translation_client,
                debug=debug)

        if full_phrase_translated == 'timeout':
            return construct_response_with_session(text=make_default_text())
        # End of translation block

        # If translation time is too big, there probably won't be enough time to fetch API, so returning default
        if context and time.time() - t1 > 0.6:
            return construct_response_with_session(text=make_default_text())

        login, password, keys_dict = choose_key(keys_dict)

        nutrition_dict = query_endpoint(
                link=keys_dict['link'],
                login=login,
                password=password,
                phrase=full_phrase_translated,
        )
        if 'error' in nutrition_dict:
            print(nutrition_dict['error'])
            write_to_cache_table(
                    initial_phrase=full_phrase,
                    nutrition_dict=nutrition_dict,
                    database_client=database_client,
                    keys_dict=keys_dict)
            return construct_response_with_session(text=make_default_text())

    response_text, total_calories = make_final_text(nutrition_dict=nutrition_dict)
    print(response_text)
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
            text=response_text + '\nСкажите "да" или "сохранить", если хотите записать этот прием пищи.',
            tts=f'{choose_case(amount=total_calories, tts_mode=True, round_to_int=True)}. Сохранить?')


if __name__ == '__main__':
    testing = '2 миллиграмма киселя, 100 грамм картошки, 100 миллиграмм чая'.lower()
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
