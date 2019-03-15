from yandex_types import YandexRequest, YandexResponse
from responses_constructors import construct_yandex_response_from_yandex_request
import datetime
from dates_transformations import transform_yandex_datetime_value_to_datetime
import typing
import functools


def if_token_number_in_interval(yandex_entity_dict: dict, *, token_number: int):
    if 'tokens' not in yandex_entity_dict:
        return False
    if 'start' not in yandex_entity_dict['tokens']:
        return False
    if 'end' not in yandex_entity_dict['tokens']:
        return False
    if yandex_entity_dict['tokens']['start'] <= \
            token_number < \
            yandex_entity_dict['tokens']['end']:
        return True
    return False


def remove_tokens_from_specific_intervals(
        *,
        tokens_list: list,
        intervals_dicts_list: typing.Iterable,
) -> list:
    result_list = []
    for token_number, token in enumerate(tokens_list):
        partial_function = functools.partial(
                if_token_number_in_interval,
                token_number=token_number)
        result = list(map(partial_function, intervals_dicts_list))
        if any(result):
            continue
        result_list.append(token)

    return result_list


def respond_delete(request: YandexRequest) -> YandexResponse:
    all_datetime_entries = [entity for entity in request.entities if
                            entity['type'] == "YANDEX.DATETIME"]

    if len(all_datetime_entries) == 0:
        target_date = datetime.date.today()
    else:
        # last detected date
        target_date = transform_yandex_datetime_value_to_datetime(
                yandex_datetime_value_dict=all_datetime_entries[-1],
        )

    tokens_without_dates_tokens = remove_tokens_from_specific_intervals(
            tokens_list=request.tokens,
            intervals_dicts_list=all_datetime_entries)

    tokens_without_delete_words = [t for t in tokens_without_dates_tokens if
                                   t not in (
                                       'удалить',
                                       'еду',
                                       'удали',
                                       'удалите'
                                       'убери',
                                       'убрать')]

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Deleted',
            tts='Deleted',
            end_session=False,
            buttons=[],
    )
