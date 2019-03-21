from decorators import timeit
from botocore.vendored.requests.exceptions import ReadTimeout, ConnectTimeout
import boto3
from yandex_types import YandexRequest
from dataclasses import replace


@timeit
def translate_text_into_english(
        *,
        russian_text: str,
        translation_client: boto3.client):

    try:
        full_phrase_translated = translation_client.translate_text(
                Text=russian_text,
                SourceLanguageCode='ru',
                TargetLanguageCode='en'
        ).get('TranslatedText')  # type:str

    except (ConnectTimeout, ReadTimeout):
        return 'Error: timeout'

    return full_phrase_translated


def string_is_only_latin_and_numbers(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True


@timeit
def translate_request(
        *,
        yandex_request: YandexRequest,
        translate_client: boto3.client,
):
    if string_is_only_latin_and_numbers(yandex_request.original_utterance):
        return yandex_request

    translated_yandex_request = replace(
            yandex_request,
            original_utterance=translate_text_into_english(
                    russian_text=yandex_request.original_utterance,
                    translation_client=translate_client,
            ),
    )  # type: YandexRequest

    if translated_yandex_request.original_utterance == 'Error: timeout':
        translated_yandex_request = replace(
                translated_yandex_request,
                error='timeout')

    return translated_yandex_request
