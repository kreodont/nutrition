from yandex_types import YandexRequest, YandexResponse
from responses_constructors import \
    construct_yandex_response_from_yandex_request, respond_request
import datetime
from dates_transformations import transform_yandex_datetime_value_to_datetime
import typing
import functools
from dynamodb_functions import delete_food, find_food_by_name_and_day, \
    get_boto3_client


def respond_nothing_to_delete(request: YandexRequest, date) -> YandexResponse:
    respond_string = f'Никакой еды не найдено за {date}. Чтобы еда появилась ' \
        f'в моей базе, необходимо не забывать говорить "сохранить"'
    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=respond_string,
            tts=respond_string,
            end_session=False,
            buttons=[],
    )


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

    respond_nothing_to_delete_with_date = functools.partial(
            respond_nothing_to_delete,
            date=target_date.date())

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

    if len(tokens_without_delete_words) == 0:
        return respond_request(
                request=request,
                responding_function=respond_nothing_to_delete_with_date)

    food_to_delete = ' '.join(tokens_without_delete_words)

    matching_food = find_food_by_name_and_day(
            database_client=get_boto3_client(
                    aws_lambda_mode=request.aws_lambda_mode,
                    service_name='dynamodb'),
            date=target_date.date(),
            food_name=food_to_delete,
            user_id=request.user_guid,
    )

    if len(matching_food) == 0:
        return respond_request(
                request=request,
                responding_function=respond_nothing_to_delete_with_date,
        )

    if len(matching_food) > 1:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=f'Несколько значений '
                f'подходят: {[i["utterance"] for i in matching_food]}. '
                f'Уточните, какое удалить?',
                tts='Несколько значений подходят.',
                end_session=False,
                buttons=[],
        )

    delete_food(database_client=get_boto3_client(
            aws_lambda_mode=request.aws_lambda_mode,
            service_name='dynamodb'),
            date=target_date,
            list_of_food_dicts=matching_food,
            user_id=request.user_guid,
    )

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=f'"{food_to_delete}" удалено',
            tts='Удалено',
            end_session=False,
            buttons=[],
    )
