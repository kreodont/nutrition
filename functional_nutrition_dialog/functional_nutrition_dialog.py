import datetime
from dataclasses import dataclass, replace
import typing
from functools import reduce, partial
import random
import boto3
import botocore.client
from botocore.vendored.requests.exceptions import ReadTimeout, ConnectTimeout
import json
import time
import requests

import dateutil

boto3_translation_client = None  # make it global for caching
boto3_database_client = None

# This cache is useful because AWS lambda can keep it's state, so no
# need to restantiate connections again. It is used in get_boto3_client
# function, I know it is mess, but 100 ms are 100 ms
global_cached_boto3_clients = {}


@dataclass(frozen=True)
class YandexRequest:
    client_device_id: str
    has_screen: bool
    timezone: str
    original_utterance: str
    is_new_session: bool
    user_guid: str
    message_id: str
    session_id: str
    entities: typing.List[typing.Dict[str, str]]
    tokens: typing.List[str]
    aws_lambda_mode: bool
    version: str
    error: str = ''

    @staticmethod
    def empty_request(*, aws_lambda_mode: bool, error: str):
        return YandexRequest(
                client_device_id='',
                has_screen=False,
                timezone='UTC',
                original_utterance='',
                entities=[],
                tokens=[],
                is_new_session=False,
                user_guid='',
                message_id='',
                session_id='',
                version='',
                aws_lambda_mode=aws_lambda_mode,
                error=error
        )

    def __repr__(self):
        return '\n'.join(
                [f'{key:20}: {self.__dict__[key]}' for
                 key in sorted(self.__dict__.keys())])


@dataclass(frozen=True)
class YandexResponse:
    client_device_id: str
    has_screen: bool
    user_guid: str
    message_id: str
    session_id: str
    response_text: str
    response_tts: str
    end_session: bool
    version: str
    buttons: typing.List[typing.Dict]

    def __repr__(self):
        return '\n'.join(
                [f'{key:20}: {self.__dict__[key]}' for
                 key in sorted(self.__dict__.keys())])


def timeit(target_function):
    def timed(*args, **kwargs):
        start_time = time.time()
        result = target_function(*args, **kwargs)
        end_time = time.time()
        milliseconds = (end_time - start_time) * 1000
        first_column = f'Function "{target_function.__name__}":'
        if target_function.__name__ == 'functional_nutrition_dialog':
            print('-' * 90)
        print(f'{first_column:80} {milliseconds:.1f} ms')
        if target_function.__name__ == 'functional_nutrition_dialog':
            print('-' * 90)
        return result

    return timed


@timeit
def get_boto3_client(
        *,
        aws_lambda_mode: bool,
        service_name: str,
        profile_name: str = 'kreodont',
        connect_timeout: float = 0.2,
        read_timeout: float = 0.4,
) -> typing.Optional[boto3.client]:
    """
    Dirty function to fetch s3_clients
    :param connect_timeout:
    :param read_timeout:
    :param aws_lambda_mode:
    :param service_name:
    :param profile_name:
    :return:
    """
    known_services = ['translate', 'dynamodb', 's3']
    if service_name in global_cached_boto3_clients:
        print(f'{service_name} client taken from cache!')
        return global_cached_boto3_clients[service_name]

    if service_name not in known_services:
        raise Exception(
                f'Not known service '
                f'name {service_name}. The following '
                f'service names known: {", ".join(known_services)}')

    if aws_lambda_mode:
        client = boto3.client(
                service_name,
                config=botocore.client.Config(
                        connect_timeout=connect_timeout,
                        read_timeout=read_timeout,
                        parameter_validation=False,
                        retries={'max_attempts': 0},
                ),
        )
    else:
        client = boto3.Session(profile_name=profile_name).client(service_name)

    global_cached_boto3_clients[service_name] = client
    return client


def fetch_one_value_from_event_dict(
        *,
        event_dict: dict,
        path: str) -> typing.Optional[typing.Any]:
    if not isinstance(event_dict, dict):
        return None
    value = None
    try:
        value = reduce(
                dict.get, [t.strip() for t in path.split('->')],
                event_dict)
    except TypeError:
        pass

    return value


@timeit
def transform_event_dict_to_yandex_request_object(
        *,
        event_dict: dict,
        aws_lambda_mode: bool,
) -> YandexRequest:
    meta = fetch_one_value_from_event_dict(
            event_dict=event_dict,
            path='meta')
    if meta is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: meta is None')

    client_device_id = fetch_one_value_from_event_dict(
            path='meta -> client_id',
            event_dict=event_dict)
    if client_device_id is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: client_id is None')
    partial_constructor = partial(YandexRequest,
                                  client_device_id=client_device_id)

    timezone = fetch_one_value_from_event_dict(
            path='meta -> timezone',
            event_dict=event_dict)
    if timezone is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: timezone is None')
    partial_constructor = partial(partial_constructor,
                                  timezone=timezone)

    has_screen = fetch_one_value_from_event_dict(
            path='meta -> interfaces -> screen',
            event_dict=event_dict)
    has_screen = False if has_screen is None else True
    partial_constructor = partial(partial_constructor,
                                  has_screen=has_screen)

    is_new_session = fetch_one_value_from_event_dict(
            path='session -> new',
            event_dict=event_dict)
    if is_new_session is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: is_new_session is None')
    partial_constructor = partial(partial_constructor,
                                  is_new_session=is_new_session)

    user_guid = fetch_one_value_from_event_dict(
            path='session -> user_id',
            event_dict=event_dict)
    if user_guid is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: user_guid is None')
    partial_constructor = partial(partial_constructor,
                                  user_guid=user_guid)

    version = fetch_one_value_from_event_dict(
            path='version',
            event_dict=event_dict)
    version = '1.0' if version is None else version
    partial_constructor = partial(partial_constructor,
                                  version=version)

    session_id = fetch_one_value_from_event_dict(
            path='session -> session_id',
            event_dict=event_dict)
    if user_guid is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: session_id is None')
    partial_constructor = partial(partial_constructor,
                                  session_id=session_id)

    message_id = fetch_one_value_from_event_dict(
            path='session -> message_id',
            event_dict=event_dict)
    if message_id is None:
        return YandexRequest.empty_request(
                aws_lambda_mode=aws_lambda_mode,
                error='Invalid request: message_id is None')
    partial_constructor = partial(partial_constructor,
                                  message_id=message_id)

    original_utterance = fetch_one_value_from_event_dict(
            path='request -> original_utterance',
            event_dict=event_dict)
    original_utterance = '' if \
        original_utterance is None \
        else original_utterance
    partial_constructor = partial(partial_constructor,
                                  original_utterance=original_utterance)

    tokens = fetch_one_value_from_event_dict(
            path='request -> nlu -> tokens',
            event_dict=event_dict)
    tokens = [] if \
        tokens is None \
        else tokens
    partial_constructor = partial(partial_constructor,
                                  tokens=tokens)

    entities = fetch_one_value_from_event_dict(
            path='request -> nlu -> entities',
            event_dict=event_dict)
    entities = [] if \
        entities is None \
        else entities
    full_yandex_request_constructor = partial(partial_constructor,
                                              entities=entities)

    return full_yandex_request_constructor(aws_lambda_mode=aws_lambda_mode)


@timeit
def transform_yandex_response_to_output_result_dict(
        *,
        yandex_response: YandexResponse) -> dict:
    response = {
        "response": {
            "text": yandex_response.response_text,
            "tts": yandex_response.response_tts,
            "end_session": yandex_response.end_session
        },
        "session": {
            "session_id": yandex_response.session_id,
            "message_id": yandex_response.message_id,
            "user_id": yandex_response.user_guid
        },
        "version": yandex_response.version
    }
    return response


@timeit
def construct_yandex_response_from_yandex_request(
        *,
        yandex_request: YandexRequest,
        text: str,
        tts: str,
        end_session: bool,
        buttons: list):
    return YandexResponse(
            client_device_id=yandex_request.client_device_id,
            has_screen=yandex_request.has_screen,
            end_session=end_session,
            message_id=yandex_request.message_id,
            session_id=yandex_request.session_id,
            user_guid=yandex_request.user_guid,
            version=yandex_request.version,
            response_text=text,
            response_tts=tts,
            buttons=buttons,
    )


def construct_response_text_from_nutrition_dict(
        *,
        nutrition_dict: dict) -> typing.Tuple[str, float]:
    response_text = ''  # type: str
    total_calories = 0.0  # type: float
    total_fat = 0.0
    total_carbohydrates = 0.0
    total_protein = 0.0
    total_sugar = 0.0

    for number, food_name in enumerate(nutrition_dict['foods']):
        calories = nutrition_dict["foods"][number].get("nf_calories", 0) or 0
        total_calories += calories
        weight = nutrition_dict['foods'][number].get(
                'serving_weight_grams', 0) or 0

        protein = nutrition_dict["foods"][number].get("nf_protein", 0) or 0
        total_protein += protein
        fat = nutrition_dict["foods"][number].get("nf_total_fat", 0) or 0
        total_fat += fat
        carbohydrates = nutrition_dict["foods"][number].get(
                "nf_total_carbohydrate", 0) or 0

        total_carbohydrates += carbohydrates
        sugar = nutrition_dict["foods"][number].get("nf_sugars", 0) or 0
        total_sugar += sugar
        number_string = ''
        if len(nutrition_dict["foods"]) > 1:
            number_string = f'{number + 1}. '
        response_text += f'{number_string}{choose_case(amount=calories)} ' \
            f'в {weight} гр.\n' \
            f'({round(protein, 1)} бел. ' \
            f'{round(fat, 1)} жир. ' \
            f'{round(carbohydrates, 1)} угл. ' \
            f'{round(sugar, 1)} сах.)\n'

    if len(nutrition_dict["foods"]) > 1:
        response_text += f'Итого: ({round(total_protein, 1)} бел. ' \
            f'{round(total_fat, 1)} жир. ' \
            f'{round(total_carbohydrates, 1)} ' \
            f'угл. {round(total_sugar, 1)} сах.' \
            f')\n_\n{choose_case(amount=total_calories)}\n_\n'

    return response_text, total_calories


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


def construct_food_yandex_response_from_food_dict(
        *,
        yandex_request: YandexRequest,
        cached_dict: dict) -> YandexResponse:
    if 'error' in cached_dict:
        return respond_i_dont_know(request=yandex_request)

    respond_text, total_calories_float = \
        construct_response_text_from_nutrition_dict(nutrition_dict=cached_dict)

    if yandex_request.has_screen:
        tts = choose_case(
                amount=total_calories_float,
                tts_mode=True,
                round_to_int=True)
    else:
        tts = respond_text

    return YandexResponse(
            client_device_id=yandex_request.client_device_id,
            has_screen=yandex_request.has_screen,
            end_session=False,
            message_id=yandex_request.message_id,
            session_id=yandex_request.session_id,
            user_guid=yandex_request.user_guid,
            version=yandex_request.version,
            response_text=respond_text,
            response_tts=tts,
            buttons=[],
    )


def respond_request(
        *,
        request: YandexRequest,
        responding_function: typing.Callable) -> YandexResponse:
    return responding_function(request)
    pass


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
    item_to_save.append({
        'time': event_time.strftime('%Y-%m-%d %H:%M:%S'),
        'foods': foods_dict,
        'utterance': utterance})
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
def clear_session(
        *,
        session_id: str,
        database_client) -> None:
    try:
        database_client.delete_item(TableName='nutrition_sessions',
                                    Key={
                                        'id': {
                                            'S': session_id,
                                        }, })
    except ReadTimeout:
        pass


@timeit
def response_with_context_when_yes_in_request(
        *,
        request: YandexRequest,
        context: dict,
        database_client
):
    # Save to database
    # Clear context
    # Say Сохранено
    update_user_table(
            database_client=database_client,
            event_time=dateutil.parser.parse(context['time']),
            foods_dict=context['foods'],
            user_id=request.user_guid,
            utterance=context['utterance'])

    clear_session(database_client=database_client,
                  session_id=request.session_id)

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Сохранено',
            tts='Сохранено',
            end_session=False,
            buttons=[],
    )


@timeit
def response_with_context_when_no_in_request(
        *,
        request: YandexRequest,
        database_client
):
    # Clear context
    # Say Забыли

    clear_session(database_client=database_client,
                  session_id=request.session_id)

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Забыли',
            tts='Забыли',
            end_session=False,
            buttons=[],
    )


@timeit
def check_if_yes_in_request(*, request: YandexRequest) -> bool:
    tokens = request.tokens
    if (
            'да' in tokens or
            'ага' in tokens or
            'конечно' in tokens or
            'хорошо' in tokens or
            'хранить' in tokens or
            'сохраняй' in tokens or
            'давай' in tokens or
            'можно' in tokens or
            'сохрани' in tokens or
            'храни' in tokens):
        return True

    return False


@timeit
def check_if_no_in_request(*, request: YandexRequest) -> bool:
    tokens = request.tokens
    if (
            'не' in tokens or
            'нет' in tokens or
            'забудь' in tokens or
            'забыть' in tokens or
            'удалить' in tokens):
        return True

    return False


@timeit
def check_if_help_in_request(*, request: YandexRequest) -> bool:
    tokens = request.tokens
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
        return True

    return False


@timeit
def respond_with_context(
        *,
        request: YandexRequest,
        context: dict,
        database_client
) -> YandexResponse:
    if check_if_no_in_request(request=request):
        return response_with_context_when_no_in_request(
                request=request,
                database_client=database_client)

    if check_if_yes_in_request(request=request):
        return response_with_context_when_yes_in_request(
                request=request,
                context=context,
                database_client=database_client)

    # We checked all possible context reaction, nothing fits,
    # so act as we don't have context at all
    return respond_without_context(request=request)


@timeit
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


def string_is_only_latin_and_numbers(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True


@timeit
def translate_request(*, yandex_request: YandexRequest):
    if string_is_only_latin_and_numbers(yandex_request.original_utterance):
        return yandex_request

    translated_yandex_request = replace(
            yandex_request,
            original_utterance=translate_text_into_english(
                    russian_text=yandex_request.original_utterance,
                    aws_lambda_mode=yandex_request.aws_lambda_mode,
            ),
    )  # type: YandexRequest

    if translated_yandex_request.original_utterance == 'Error: timeout':
        translated_yandex_request = replace(
                translated_yandex_request,
                error='timeout')

    return translated_yandex_request


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
        return {'fatal': str(e)}

    if response.status_code != 200:
        return {'error': response.text}

    try:
        nutrition_dict = json.loads(response.text)
    except Exception as e:
        return {'fatal': f'Failed to parse food json: {e}'}

    if 'foods' not in nutrition_dict or not nutrition_dict['foods']:
        return {'fatal': f'Tag foods not found or empty: {nutrition_dict}'}

    return nutrition_dict


@timeit
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
def save_session(
        *,
        session_id: str,
        event_time: datetime.datetime,
        foods_dict: dict,
        utterance: str,
        database_client) -> None:

    database_client.put_item(
            TableName='nutrition_sessions',
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
def write_to_cache_table(
        *,
        initial_phrase: str,
        nutrition_dict: dict,
        database_client,
        keys_dict: dict) -> None:
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
def respond_without_context(request: YandexRequest) -> YandexResponse:
    database_client = get_boto3_client(
            aws_lambda_mode=request.aws_lambda_mode,
            service_name='dynamodb',
    )

    keys_dict, cached_dict = get_from_cache_table(
            request_text=request.original_utterance,
            database_client=database_client)

    if 'error' in keys_dict:
        return respond_i_dont_know(request=request)

    if cached_dict:
        return construct_food_yandex_response_from_food_dict(
                yandex_request=request,
                cached_dict=cached_dict)

    request_with_replacements = russian_replacements_in_original_utterance(
            yandex_request=request)

    translated_request = translate_request(
            yandex_request=request_with_replacements)

    if translated_request.error:
        return respond_i_dont_know(request=translated_request)

    login, password, keys_dict = choose_key(keys_dict)
    nutrition_dict = query_endpoint(
            link=keys_dict['link'],
            login=login,
            password=password,
            phrase=translated_request.original_utterance)

    # if we recevied negative response,
    if 'fatal' in nutrition_dict:
        return respond_i_dont_know(request=translated_request)

    write_to_cache_table(
            initial_phrase=request.original_utterance,
            nutrition_dict=nutrition_dict,
            database_client=database_client,
            keys_dict=keys_dict)

    if 'error' in nutrition_dict:
        return respond_i_dont_know(request=translated_request)

    save_session(
            session_id=translated_request.session_id,
            database_client=database_client,
            event_time=datetime.datetime.now(),
            foods_dict=nutrition_dict,
            utterance=request.original_utterance)

    return construct_food_yandex_response_from_food_dict(
            yandex_request=request,
            cached_dict=nutrition_dict,
    )


@timeit
def get_from_cache_table(
        *,
        request_text: str,
        database_client: boto3.client) -> typing.Tuple[dict, dict]:
    keys_dict = {}
    food_dict = {}
    try:
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
    except (ConnectTimeout, ReadTimeout):
        return {'error': 'timeout'}, {'error': 'timeout'}

    for item in items['Responses']['nutrition_cache']:
        if item['initial_phrase']['S'] == '_key':
            keys_dict = json.loads(item['response']['S'])
        if item['initial_phrase']['S'] == request_text:
            food_dict = json.loads(item['response']['S'])

    return keys_dict, food_dict


@timeit
def respond_greeting_phrase(request: YandexRequest) -> YandexResponse:
    greeting_text = 'Какую еду записать?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=greeting_text,
            tts=greeting_text,
            end_session=False,
            buttons=[],
    )


@timeit
def respond_i_dont_know(request: YandexRequest) -> YandexResponse:
    first_parts_list = [
        'Это не похоже на название еды. Попробуйте сформулировать иначе',
        'Хм. Не могу понять что это. Попробуйте сказать иначе',
        'Такой еды я пока не знаю. Попробуйте сказать иначе'
    ]

    food_examples_list = ['Бочка варенья и коробка печенья',
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

    full_generated_text = f"{random.choice(first_parts_list)}, " \
        f"например: {random.choice(food_examples_list)}"
    if request.has_screen:
        tts = "Попробуйте сказать иначе"
    else:
        tts = full_generated_text

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=full_generated_text,
            tts=tts,
            buttons=[],
            end_session=False,
    )


@timeit
def check_if_new_session(yandex_request: YandexRequest):
    return yandex_request.is_new_session


@timeit
def fetch_context_from_dynamo_database(
        *,
        aws_lambda_mode: bool,
        session_id: str,
) -> dict:
    try:
        database_client = get_boto3_client(
                aws_lambda_mode=aws_lambda_mode,
                service_name='dynamodb')

        result = database_client.get_item(
                TableName='nutrition_sessions',
                Key={'id': {'S': session_id}})

    except (ConnectTimeout, ReadTimeout):
        return {}

    if 'Item' not in result:
        return {}
    else:
        try:
            return json.loads(result['Item']['value']['S'])
        except json.decoder.JSONDecodeError:
            return {}


def is_help_request(request: YandexRequest):
    tokens = request.tokens
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
        return True
    return False


def respond_help(request: YandexRequest) -> YandexResponse:
    help_text = 'Я считаю калории. Просто скажите что вы съели, а я скажу ' \
                'сколько в этом было калорий. Например: соевое молоко с ' \
                'хлебом. Потом я спрошу надо ли сохранить этот прием пищи, и ' \
                'если вы скажете да, я запишу его в свою базу данных. Можно ' \
                'сказать не просто да, а указать время приема пищи, ' \
                'например: да, вчера в 9 часов 30 минут. После того, как ' \
                'прием пищи сохранен, вы сможете узнать свое суточное ' \
                'потребление калорий с помощью команды "что я ел(а)?". ' \
                'При этом также можно указать время, например: "Что я ел ' \
                'вчера?" или "Что я ела неделю назад?". Если какая-то еда ' \
                'была внесена ошибочно, можно сказать "Удалить соевое ' \
                'молоко с хлебом".  Прием пищи "Соевое молоко с хлебом" ' \
                'будет удален'

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=help_text,
            tts=help_text,
            end_session=False,
            buttons=[],
    )


def is_thanks_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in (
            'спасибо', 'молодец', 'отлично', 'ты классная', 'классная штука',
            'классно', 'ты молодец', 'круто', 'обалдеть', 'прикольно',
            'клево', 'ништяк'):
        return True
    return False


def respond_thanks(request: YandexRequest) -> YandexResponse:
    welcome_phrases = [
        'Спасибо, я стараюсь',
        'Спасибо за комплимент',
        'Приятно быть полезной',
        'Доброе слово и боту приятно']
    chosen_welcome_phrase = random.choice(welcome_phrases)
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=chosen_welcome_phrase,
            tts=chosen_welcome_phrase,
            end_session=False,
            buttons=[],
    )


def is_hello_request(request: YandexRequest):
    tokens = request.tokens
    if (
            'привет' in tokens or
            'здравствуй' in tokens or
            'здравствуйте' in tokens or
            'хелло' in tokens or
            'hello' in tokens or
            'приветик' in tokens
    ):
        return True
    return False


def is_human_meat_request(request: YandexRequest):
    tokens = request.tokens
    full_phrase = request.original_utterance
    if [t for t in tokens if 'человеч' in t] or \
            tokens == ['мясо', 'человека'] or \
            full_phrase in ('человек',):
        return True
    return False


def respond_human_meat(request: YandexRequest) -> YandexResponse:
    respond_string = 'Доктор Лектер, это вы?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def respond_hello(request: YandexRequest) -> YandexResponse:
    respond_string = 'Здравствуйте. А теперь расскажите что вы съели, а я ' \
                     'скажу сколько там было калорий и питательных веществ.'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_goodbye_request(request: YandexRequest):
    tokens = request.tokens
    full_phrase = request.original_utterance
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
        return True
    return False


def respond_goodbye(request: YandexRequest) -> YandexResponse:
    respond_string = 'До свидания'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=True,
            buttons=[],
    )


def is_eat_cat_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('кошка', 'кошку', 'кот', 'кота', 'котенок', 'котенка'):
        return True
    return False


def respond_eat_cat(request: YandexRequest) -> YandexResponse:
    respond_string = 'Нееш, падумой'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_eat_poop_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('говно', 'какашка', 'кака', 'дерьмо',
                       'фекалии', 'какахе', 'какахи'):
        return True
    return False


def respond_eat_poop(request: YandexRequest) -> YandexResponse:
    respond_string = 'Вы имели в виду "Сладкий хлеб"?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_i_think_too_much_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('это много', 'это мало', 'что-то много',
                       'что-то мало', 'так много'):
        return True
    return False


def respond_i_think_too_much(request: YandexRequest) -> YandexResponse:
    respond_string = 'Если вы нашли ошибку, напишите моему разработчику, ' \
                     'и он объяснит мне, как правильно'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_dick_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('хуй', 'моржовый хуй', 'хер'):
        return True
    return False


def respond_dick(request: YandexRequest) -> YandexResponse:
    respond_string = 'С солью или без соли?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def is_nothing_to_add_request(request: YandexRequest):
    full_phrase = request.original_utterance
    if full_phrase in ('никакую', 'ничего', 'никакой'):
        return True
    return False


def respond_nothing_to_add(request: YandexRequest) -> YandexResponse:
    respond_string = 'Хорошо, дайте знать, когда что-то появится'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


def respond_one_of_predefined_phrases(
        request: YandexRequest) -> typing.Optional[YandexResponse]:
    # Respond long phrases
    if len(request.original_utterance) >= 100:
        return respond_request(
                request=request,
                responding_function=respond_text_too_long)

    # Respond help requests
    if check_if_help_in_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_help)

    if is_thanks_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_thanks)

    if is_hello_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_hello)

    if is_goodbye_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_goodbye)

    if is_human_meat_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_human_meat)

    if is_eat_cat_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_eat_cat)

    if is_eat_poop_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_eat_poop)

    if is_i_think_too_much_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_i_think_too_much)

    if is_dick_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_dick)

    if is_nothing_to_add_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_nothing_to_add)


def respond_text_too_long(request: YandexRequest) -> YandexResponse:
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Ой, текст слишком длинный. Давайте попробуем частями?',
            tts='Ой, текст слишком длинный. Давайте попробуем частями?',
            end_session=False,
            buttons=[],
    )


def respond_existing_session(yandex_request: YandexRequest):
    context = fetch_context_from_dynamo_database(
            aws_lambda_mode=yandex_request.aws_lambda_mode,
            session_id=yandex_request.session_id,
    )

    database_client = get_boto3_client(
            aws_lambda_mode=yandex_request.aws_lambda_mode,
            service_name='dynamodb')

    if context:
        return partial(
                respond_with_context,
                context=context,
                database_client=database_client)(request=yandex_request)
    else:
        return respond_without_context(request=yandex_request)


@timeit
def translate_text_into_english(
        *,
        russian_text: str, aws_lambda_mode: bool):
    translation_client = get_boto3_client(
            aws_lambda_mode=aws_lambda_mode,
            service_name='translate')

    try:
        full_phrase_translated = translation_client.translate_text(
                Text=russian_text,
                SourceLanguageCode='ru',
                TargetLanguageCode='en'
        ).get('TranslatedText')  # type:str

    except (ConnectTimeout, ReadTimeout):
        return 'Error: timeout'

    return full_phrase_translated


@timeit
def mock_incoming_event(*, phrase: str, has_screen: bool = True) -> dict:
    if has_screen:
        interfaces = {"screen": {}}
    else:
        interfaces = {}
    return {
        "meta": {
            "client_id": "ru.yandex.searchplugin/7.16 (none none; android "
                         "4.4.2)",
            "interfaces": interfaces,
            "locale": "ru-RU",
            "timezone": "UTC"
        },
        "request": {
            "command": phrase,
            "nlu": {
                "entities": [],
                "tokens": phrase.lower().split()
            },
            "original_utterance": phrase,
            "type": "SimpleUtterance"
        },
        "session": {
            "message_id": 3,
            "new": False,
            "session_id": "2600748f-a3029350-a94653be-1508e64a",
            "skill_id": "2142c27e-6062-4899-a43b-806f2eddeb27",
            "user_id": "E401738E621D9AAC04AB162E44F39B3"
                       "ABDA23A5CB2FF19E394C1915ED45CF467"
        },
        "version": "1.0"
    }


@timeit
def functional_nutrition_dialog(event: dict, context: dict) -> dict:
    """
    Main lambda entry point
    # event:dict ->
    # YandexRequest:YandexRequest ->
    # YandexResponse:YandexResponse ->
    # response:dict
    """
    yandex_request = transform_event_dict_to_yandex_request_object(
            event_dict=event,
            aws_lambda_mode=bool(context),
    )

    if yandex_request.error:
        # Exit immediatelly in case of mailformed request
        return transform_yandex_response_to_output_result_dict(
                yandex_response=construct_yandex_response_from_yandex_request(
                        yandex_request=yandex_request,
                        text=yandex_request.error,
                        tts=yandex_request.error,
                        buttons=[],
                        end_session=True,
                ))

    # there can be many hardcoded responses, need to check all of them before
    # querying any databases
    any_predifined_response = respond_one_of_predefined_phrases(
            request=yandex_request)

    if any_predifined_response:
        # If predefined answer given, forget all previous food, since
        # conversation topic has been already changed
        clear_session(
                session_id=yandex_request.session_id,
                database_client=get_boto3_client(
                        aws_lambda_mode=yandex_request.aws_lambda_mode,
                        service_name='dynamodb',
                )
        )
        return transform_yandex_response_to_output_result_dict(
                yandex_response=any_predifined_response)

    if yandex_request.is_new_session:
        responding_function = respond_greeting_phrase
    else:
        responding_function = respond_existing_session

    return transform_yandex_response_to_output_result_dict(
            yandex_response=respond_request(
                    request=yandex_request,
                    responding_function=responding_function,
            )
    )


if __name__ == '__main__':
    # print(translate_text_into_english(
    #         russian_text='Ну прям очень длинный текст, ',
    #         aws_lambda_mode=True))
    print(functional_nutrition_dialog(
            event=mock_incoming_event(
                    phrase='200 грамм брокколи и 100 грамм шпината',
                    has_screen=True),
            context={}))
