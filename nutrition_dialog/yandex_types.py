from dataclasses import dataclass, replace
import typing
from functools import partial, reduce
from DialogContext import DialogContext


@dataclass(frozen=True)
class YandexRequest:
    """
    Request example:
    {
  "meta": {
    "client_id": "ru.yandex.searchplugin/7.16 (none none; android 4.4.2)",
    "interfaces": {
      "account_linking": {},
      "payments": {},
      "screen": {}
    },
    "locale": "ru-RU",
    "timezone": "UTC"
  },
  "request": {
    "command": "",
    "nlu": {
      "entities": [],
      "tokens": []
    },
    "original_utterance": "",
    "type": "SimpleUtterance"
  },
  "session": {
    "message_id": 0,
    "new": true,
    "session_id": "12447be0-7302eba2-5cb2629b-7eeb8bac",
    "skill_id": "2142c27e-6062-4899-a43b-806f2eddeb27",
    "user_id": "E401738E621D9AAC04AB162E44F39B3ABDA23A5CB2FF19E39
    4C1915ED45CF467"
  },
  "version": "1.0"
}
    """
    client_device_id: str  # meta -> client_id
    has_screen: bool  # meta -> interfaces -> screen
    timezone: str  # meta -> timezone
    original_utterance: str  # request -> original_utterance
    command: str  # request -> command
    is_new_session: bool  # session -> new
    user_guid: str  # session -> user_id
    message_id: int  # session -> message_id, starts from 0
    session_id: str  # session -> session_id
    entities: typing.List[typing.Dict[str, str]]  # request -> nlu -> entities
    tokens: typing.List[str]  # request -> nlu -> tokens
    aws_lambda_mode: bool  # whether launched in cloud or not
    version: str  # version, for now always "1.0"
    intents_matching_dict: typing.Dict[object, int]  # Each intent
    # puts here percent of matching. If one of intents puts here 100, that
    # means that this intent fits perfectly and no need to check others.
    context: typing.Optional[DialogContext]  # current dialog context,
    # loaded from DynamoDB
    food_dict: dict  # Response from the API
    api_keys: dict  # To query API
    chosen_intent: typing.Any = None  # Intent which will be executed.
    translated_phrase: str = ''  # Phrase translated into English
    # Can be
    # overrided depending on context
    error: str = ''  # if any errors parsing Yandex dictionary
    use_food_cache: bool = True  # for testing purposes
    write_to_food_cache: bool = True  # for testing
    food_already_in_cache: bool = False  # Not to write it again
    automatic_save: bool = False  # If set yes, don't ask a user if he wants
    # to save the food, save it automatically and don't save context

    @staticmethod
    def empty_request(*, aws_lambda_mode: bool, error: str):
        """
        To show errors
        :param aws_lambda_mode:
        :param error:
        :return:
        """
        return YandexRequest(
                client_device_id='',
                has_screen=False,
                timezone='UTC',
                original_utterance='',
                entities=[],
                tokens=[],
                is_new_session=False,
                user_guid='',
                message_id=0,
                session_id='',
                version='',
                command='',
                aws_lambda_mode=aws_lambda_mode,
                error=error,
                context=None,
                intents_matching_dict={},
                translated_phrase='',
                food_dict={},
                api_keys={},
        )

    def set_context(self, context: typing.Optional[DialogContext]):
        return replace(self, context=context)

    def set_chosen_intent(self, chosen_intent):
        return replace(self, chosen_intent=chosen_intent)

    def set_translated_phrase(self, translated):
        return replace(self, translated_phrase=translated)

    def set_original_utterance(self, utterance):
        return replace(self, original_utterance=utterance)

    def set_food_dict(self, food_dict):
        return replace(self, food_dict=food_dict)

    def set_api_keys(self, api_keys: dict):
        return replace(self, api_keys=api_keys)

    def set_food_already_in_cache(self):
        return replace(self, food_already_in_cache=True)

    def __repr__(self):
        return '\n'.join(
                [f'{key:20}: {self.__dict__[key]}' for
                 key in sorted(self.__dict__.keys())]) + '\n\n'


@dataclass(frozen=True)
class YandexResponse:
    initial_request: YandexRequest  # initial request
    response_text: str  # Text that will be shown to the user
    response_tts: str  # Text that will be spoken to the user
    end_session: bool  # If the last message in dialog and we should exit
    should_clear_context: bool  # whether clear old contex or not
    buttons: typing.List[typing.Dict]  # buttons that should
    # be shown to the user
    context_to_write: typing.Optional[DialogContext]

    def __repr__(self):
        return '\n'.join(
                [f'{key:20}: {self.__dict__[key]}' for
                 key in sorted(self.__dict__.keys())])


def transform_event_dict_to_yandex_request_object(
        *,
        event_dict: dict,
        aws_lambda_mode: bool,
) -> YandexRequest:
    """
    Reads the dict from yandex and try to construct
    YandexRequest object out of it
    :param event_dict:
    :param aws_lambda_mode:
    :return:
    """
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

    command = fetch_one_value_from_event_dict(
            path='request -> command',
            event_dict=event_dict)

    partial_constructor = partial(
            partial_constructor,
            command=command)

    tokens = fetch_one_value_from_event_dict(
            path='request -> nlu -> tokens',
            event_dict=event_dict)

    tokens = [] if tokens is None else tokens

    partial_constructor = partial(partial_constructor,
                                  tokens=tokens)

    entities = fetch_one_value_from_event_dict(
            path='request -> nlu -> entities',
            event_dict=event_dict,)
    entities = [] if entities is None else entities
    full_yandex_request_constructor = partial(
        partial_constructor,
        entities=entities,
        context=None,
        intents_matching_dict={},
        food_dict={},
        api_keys={},
        write_to_food_cache=event_dict.get('write_to_food_cache'),

                                              )

    return full_yandex_request_constructor(aws_lambda_mode=aws_lambda_mode)


def fetch_one_value_from_event_dict(
        *,
        event_dict: dict,
        path: str) -> typing.Optional[typing.Any]:
    """
    To extract data from multilevel dictionary using the following syntax:
    'meta -> interfaces -> screen'
    :param event_dict:
    :param path:
    :return:
    """
    if not isinstance(event_dict, dict):
        return None
    value = None
    try:
        value = reduce(
                dict.get,
                [t.strip() for t in path.split('->')],
                event_dict)
    except TypeError:
        pass

    return value


def construct_yandex_response_from_yandex_request(
        *,
        yandex_request: YandexRequest,
        text: str,
        tts: str = '',
        end_session: bool = False,
        buttons: list = (),
        should_clear_context: bool = False,
        new_context_to_write: DialogContext = None,
):
    if tts == '':
        tts = text

    return YandexResponse(
            initial_request=yandex_request,
            end_session=end_session,
            response_text=text,
            response_tts=tts,
            buttons=buttons,
            should_clear_context=should_clear_context,
            context_to_write=new_context_to_write,
    )


def transform_yandex_response_to_output_result_dict(
        *,
        yandex_response: YandexResponse) -> dict:
    """
    Converts YandexResponse to output dictionary
    :param yandex_response:
    :return:
    """
    response = {
        "response": {
            "text": yandex_response.response_text,
            "tts": yandex_response.response_tts,
            "end_session": yandex_response.end_session
        },
        "session": {
            "session_id": yandex_response.initial_request.session_id,
            "message_id": yandex_response.initial_request.message_id,
            "user_id": yandex_response.initial_request.user_guid
        },
        "version": yandex_response.initial_request.version
    }
    return response
