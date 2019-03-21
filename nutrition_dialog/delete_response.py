from yandex_types import YandexRequest, YandexResponse
from responses_constructors import \
    construct_yandex_response_from_yandex_request, respond_request
import datetime
from dates_transformations import transform_yandex_datetime_value_to_datetime
import typing
import functools
from dynamodb_functions import delete_food, find_all_food_names_for_day, \
    get_boto3_client
import re


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


def respond_food_to_delete_not_found(
        request: YandexRequest,
        date: datetime,
        food_to_delete_name: str,
        found_foods: typing.List[dict],
) -> YandexResponse:
    respond_string = f'"{food_to_delete_name}" не найдено за {date}. ' \
        f'Найдено: {[food["utterance"] for food in found_foods]}. Чтобы ' \
        f'удалить еду, нужно произнести Удалить "еда" ' \
        f'именно в том виде, как она записана. ' \
        f'Например, удалить {found_foods[0]["utterance"]}. Также можно ' \
        f'удалить еду по номеру, например: удалить номер 2'
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

    # if no dates found in request, assuming deletion for today was requested
    if len(all_datetime_entries) == 0:
        target_date = datetime.date.today()
    else:
        # last detected date
        last_detected_date = all_datetime_entries[-1]
        target_date = transform_yandex_datetime_value_to_datetime(
                yandex_datetime_value_dict=last_detected_date,
        ).date()

    respond_nothing_to_delete_with_date = functools.partial(
            respond_nothing_to_delete,
            date=target_date)

    tokens_without_dates_tokens = remove_tokens_from_specific_intervals(
            tokens_list=request.original_utterance.split(),
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

    all_food_for_date = find_all_food_names_for_day(
            database_client=get_boto3_client(
                    aws_lambda_mode=request.aws_lambda_mode,
                    service_name='dynamodb'),
            date=target_date,
            user_id=request.user_guid,
    )

    if len(all_food_for_date) == 0:
        return respond_request(
                request=request,
                responding_function=functools.partial(
                        respond_nothing_to_delete_with_date,
                )
        )

    if food_to_delete in ('все', 'всё'):
        delete_food(database_client=get_boto3_client(
                aws_lambda_mode=request.aws_lambda_mode,
                service_name='dynamodb'),
                date=target_date,
                list_of_food_to_delete_dicts=all_food_for_date,
                list_of_all_food_dicts=all_food_for_date,
                user_id=request.user_guid,
        )

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=f'Вся еда удалена за {target_date}',
                tts='Удалено',
                end_session=False,
                buttons=[],
        )

    # Delete food by number
    if re.match(r'номер \d+', food_to_delete):
        food_number = int(float(food_to_delete.replace('номер ', '')))
        if food_number <= 0:
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'Неправильный номер {food_number}',
                    tts=f'Неправильный номер {food_number}',
                    end_session=False,
                    buttons=[],
            )

        if food_number > len(all_food_for_date):
            return construct_yandex_response_from_yandex_request(
                    yandex_request=request,
                    text=f'За дату {target_date} найдено '
                    f'только {len(all_food_for_date)} приемов пищи, '
                    f'не могу удалить {food_number}',
                    tts=f'Неправильный номер {food_number}',
                    end_session=False,
                    buttons=[],
            )
        food_to_delete = [all_food_for_date[food_number - 1], ]
        delete_food(database_client=get_boto3_client(
                aws_lambda_mode=request.aws_lambda_mode,
                service_name='dynamodb'),
                date=target_date,
                list_of_food_to_delete_dicts=food_to_delete,
                list_of_all_food_dicts=all_food_for_date,
                user_id=request.user_guid,
        )

        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=f'Еда номер {food_number} удалена',
                tts='Удалено',
                end_session=False,
                buttons=[],
        )

    matching_food = []
    for food in all_food_for_date:
        if (food['utterance'] and food_to_delete.strip() ==
                food['utterance'].replace(',', '').strip()):
            matching_food.append(food)

    if len(matching_food) == 0:
        return respond_request(
                request=request,
                responding_function=functools.partial(
                        respond_food_to_delete_not_found,
                        date=target_date,
                        food_to_delete_name=food_to_delete,
                        found_foods=all_food_for_date)
        )

    if len(matching_food) > 1:
        return construct_yandex_response_from_yandex_request(
                yandex_request=request,
                text=f'Несколько значений '
                f'подходят: {[i["utterance"] for i in matching_food]}. '
                f'Уточните, какое удалить? Можно удалить по номеру, сказав '
                f'"Удали номер 1", например',
                tts='Несколько значений подходят.',
                end_session=False,
                buttons=[],
        )

    delete_food(database_client=get_boto3_client(
            aws_lambda_mode=request.aws_lambda_mode,
            service_name='dynamodb'),
            date=target_date,
            list_of_food_to_delete_dicts=matching_food,
            list_of_all_food_dicts=all_food_for_date,
            user_id=request.user_guid,
    )

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text=f'"{food_to_delete}" удалено',
            tts='Удалено',
            end_session=False,
            buttons=[],
    )
