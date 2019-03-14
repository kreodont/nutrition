from yandex_types import YandexRequest, YandexResponse
from responses_constructors import construct_yandex_response_from_yandex_request




def respond_delete(request: YandexRequest) -> YandexResponse:

    return construct_yandex_response_from_yandex_request(
            yandex_request=request,
            text='Deleted',
            tts='Deleted',
            end_session=False,
            buttons=[],
    )
