import datetime
from dataclasses import dataclass
import typing
from functools import reduce, partial
import random
import boto3
import botocore.client
import json

import dateutil

boto3_translation_client = None  # make it global for caching
boto3_database_client = None


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

    @staticmethod
    def empty_request(*, aws_lambda_mode):
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


def get_boto3_clients(*, aws_lambda_mode: bool):
    # global boto3_database_client, boto3_translation_client

    def get_local_boto3_clients():
        global boto3_database_client, boto3_translation_client
        boto3_translation_client = boto3.Session(
                profile_name='kreodont').client('translate')
        boto3_database_client = boto3.Session(
                profile_name='kreodont').client('dynamodb')
        return boto3_translation_client, boto3_database_client

    def get_aws_boto3_clients():
        global boto3_database_client, boto3_translation_client
        config = botocore.client.Config(
                connect_timeout=0.5,
                retries={'max_attempts': 0},
        )
        boto3_translation_client = boto3.client('translate', config=config)
        boto3_database_client = boto3.client('dynamodb', config=config)
        return boto3_translation_client, boto3_database_client

    def return_cached_clients():
        return boto3_translation_client, boto3_database_client

    # already cached
    if boto3_translation_client and boto3_database_client:
        return return_cached_clients

    if aws_lambda_mode:
        return get_aws_boto3_clients

    return get_local_boto3_clients


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


def transform_event_dict_to_yandex_request_object(
        *,
        event_dict: dict,
        aws_lambda_mode: bool,
) -> typing.Tuple[YandexRequest, str]:
    meta = fetch_one_value_from_event_dict(
            event_dict=event_dict,
            path='meta')
    if meta is None:
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: meta is None'

    client_device_id = fetch_one_value_from_event_dict(
            path='meta -> client_id',
            event_dict=event_dict)
    if client_device_id is None:
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: client_id is None'
    partial_constructor = partial(YandexRequest,
                                  client_device_id=client_device_id)

    timezone = fetch_one_value_from_event_dict(
            path='meta -> timezone',
            event_dict=event_dict)
    if timezone is None:
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: timezone is None'
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
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: is_new_session is None'
    partial_constructor = partial(partial_constructor,
                                  is_new_session=is_new_session)

    user_guid = fetch_one_value_from_event_dict(
            path='session -> user_id',
            event_dict=event_dict)
    if user_guid is None:
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: user_guid is None'
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
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: session_id is None'
    partial_constructor = partial(partial_constructor,
                                  session_id=session_id)

    message_id = fetch_one_value_from_event_dict(
            path='session -> message_id',
            event_dict=event_dict)
    if message_id is None:
        return YandexRequest.empty_request(aws_lambda_mode=aws_lambda_mode), \
               'Invalid request: message_id is None'
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

    return full_yandex_request_constructor(aws_lambda_mode=aws_lambda_mode), ''


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


def respond_request(
        *,
        request: YandexRequest,
        responding_function: typing.Callable) -> YandexResponse:
    return responding_function(request)
    pass


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


def clear_session(
        *,
        session_id: str,
        database_client) -> None:
    database_client.delete_item(TableName='nutrition_sessions',
                                Key={
                                    'id': {
                                        'S': session_id,
                                    }, })


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


def respond_without_context(request: YandexRequest) -> YandexResponse:
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Without context',
            tts='Without context',
            end_session=False,
            buttons=[],
    )


def respond_greeting_phrase(request: YandexRequest) -> YandexResponse:
    greeting_text = 'Какую еду записать?'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=greeting_text,
            tts=greeting_text,
            end_session=False,
            buttons=[],
    )


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


def check_if_new_session(yandex_request: YandexRequest):
    return yandex_request.is_new_session


def fetch_context_from_dynamo_database(
        *,
        aws_lambda_mode: bool,
        session_id: str,
) -> dict:

    _, database_client = get_boto3_clients(aws_lambda_mode=aws_lambda_mode)()
    result = database_client.get_item(
            TableName='nutrition_sessions', Key={'id': {'S': session_id}})
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


def respond_one_of_predefined_phrases(
        request: YandexRequest) -> typing.Optional[YandexResponse]:
    if len(request.original_utterance) >= 100:
        return respond_request(
                request=request,
                responding_function=respond_text_too_long)

    if check_if_help_in_request(request=request):
        return respond_request(
                request=request,
                responding_function=respond_help)


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

    _, database_client = get_boto3_clients(
            aws_lambda_mode=yandex_request.aws_lambda_mode)()

    return partial(
            respond_with_context,
            context=context,
            database_client=database_client,)(request=yandex_request) if \
        context else respond_without_context(request=yandex_request)


def functional_nutrition_dialog(event: dict, context: dict) -> dict:
    """
    Main lambda entry point
    # event:dict ->
    # YandexRequest:YandexRequest ->
    # YandexResponse:YandexResponse ->
    # response:dict
    """

    yandex_request, error = transform_event_dict_to_yandex_request_object(
            event_dict=event,
            aws_lambda_mode=bool(context),
    )

    if error:
        # Exit immediatelly in case of mailformed request
        return transform_yandex_response_to_output_result_dict(
                yandex_response=construct_yandex_response_from_yandex_request(
                        yandex_request=yandex_request,
                        text=error,
                        tts=error,
                        buttons=[],
                        end_session=True,
                ))

    # there can be many hardcoded responses, need to check all of them before
    # querying any databases
    any_predifined_response = respond_one_of_predefined_phrases(
            request=yandex_request)
    if any_predifined_response:
        # TODO: Should I clear context here? Maybe yes
        return transform_yandex_response_to_output_result_dict(
                yandex_response=any_predifined_response)

    # Don't check session context if it's the first message, maybe this
    # should be changed. For example, the user left without his food to be
    # saved, then returned later and said Yes. Probably not worth doing.
    responding_function = respond_greeting_phrase if \
        yandex_request.is_new_session else \
        respond_existing_session

    return transform_yandex_response_to_output_result_dict(
            yandex_response=respond_request(
                    request=yandex_request,
                    responding_function=responding_function))


if __name__ == '__main__':
    test_command = 'как пользоваться?'
    print(functional_nutrition_dialog(event={
        "meta": {
            "client_id": "ru.yandex.searchplugin/7.16 (none none; android "
                         "4.4.2)",
            "interfaces": {
                "screen": {}
            },
            "locale": "ru-RU",
            "timezone": "UTC"
        },
        "request": {
            "command": "собака",
            "nlu": {
                "entities": [],
                "tokens": test_command.lower().split()
            },
            "original_utterance": test_command,
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
    }, context={}))
