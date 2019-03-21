from dataclasses import dataclass
import typing
from decorators import timeit
from functools import partial, reduce
import hashlib


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
    tokens = [] if tokens is None else tokens

    partial_constructor = partial(partial_constructor,
                                  tokens=tokens)

    entities = fetch_one_value_from_event_dict(
            path='request -> nlu -> entities',
            event_dict=event_dict)
    entities = [] if entities is None else entities

    full_yandex_request_constructor = partial(partial_constructor,
                                              entities=entities)

    return full_yandex_request_constructor(aws_lambda_mode=aws_lambda_mode)


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
    print(f'НАВЫК_{log_hash(yandex_response)}: {yandex_response.response_text}')
    return response


def log_hash(
        request_or_response,
) -> str:
    session_id = request_or_response.session_id
    message_id = str(request_or_response.message_id)
    return str(int(hashlib.sha1(session_id.encode()).hexdigest(),
                   16) % (10 ** 3)) + '_' + message_id
