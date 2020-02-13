import typing
from russian_language import choose_case
from yandex_types import YandexRequest, YandexResponse
from decorators import timeit
import standard_responses as sr


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

    if len(nutrition_dict["foods"]) > 1:  # more than one food
        response_text += f'Итого: ({round(total_protein, 1)} бел. ' \
            f'{round(total_fat, 1)} жир. ' \
            f'{round(total_carbohydrates, 1)} ' \
            f'угл. {round(total_sugar, 1)} сах.' \
            f')\n_\n{choose_case(amount=total_calories)}\n_\n'

    return response_text, total_calories


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


def construct_food_yandex_response_from_food_dict(
        *,
        yandex_request: YandexRequest,
        cached_dict: dict) -> YandexResponse:
    if 'error' in cached_dict:
        return sr.respond_i_dont_know(request=yandex_request)

    respond_text, total_calories_float = \
        construct_response_text_from_nutrition_dict(nutrition_dict=cached_dict)

    respond_text += '\nСкажите "да" или "сохранить", если ' \
                    'хотите записать этот прием пищи.'

    if yandex_request.has_screen:
        tts = choose_case(
                amount=total_calories_float,
                tts_mode=True,
                round_to_int=True) + '. Сохранить?'
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
