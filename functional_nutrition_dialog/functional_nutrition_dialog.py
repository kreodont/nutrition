from dataclasses import dataclass
import typing
from functools import reduce, partial
import random


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


def respond_with_context(*, request: YandexRequest, context) -> YandexResponse:
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='With context' + str(context),
            tts='With context',
            end_session=False,
            buttons=[],
    )


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


def fetch_context_from_dynamo_database() -> dict:
    return {}


def respond_existing_session(yandex_request: YandexRequest):
    context = fetch_context_from_dynamo_database()
    return partial(respond_with_context, context)(yandex_request) if \
        context else respond_without_context(yandex_request)


def functional_nutrition_dialog(event: dict, context: dict) -> dict:
    """
    Main lambda entry point
    :param event:
    :param context:
    :return:
    """
    if context:
        pass

    yandex_request, error = transform_event_dict_to_yandex_request_object(
            event_dict=event,
            aws_lambda_mode=bool(context),
    )

    if error:
        # Exit immediatelly
        return transform_yandex_response_to_output_result_dict(
                yandex_response=construct_yandex_response_from_yandex_request(
                        yandex_request=yandex_request,
                        text=error,
                        tts=error,
                        buttons=[],
                        end_session=True,
                ))

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

    # event:dict ->
    # YandexRequest:YandexRequest ->
    # check_context:YandexRequest ->
    # choose_answer:str ->
    # YandexResponse:YandexResponse ->
    # response:dict


if __name__ == '__main__':
    test_command = '33 коровы'
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
            "original_utterance": "собака",
            "type": "SimpleUtterance"
        },
        "session": {
            "message_id": 3,
            "new": False,
            "session_id": "4fc9367a-85300422-75187a15-4553186",
            "skill_id": "2142c27e-6062-4899-a43b-806f2eddeb27",
            "user_id": "E401738E621D9AAC04AB162E44F39B3"
                       "ABDA23A5CB2FF19E394C1915ED45CF467"
        },
        "version": "1.0"
    }, context={}))
