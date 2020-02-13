import json
import os
import re

from decorators import timeit
from botocore.vendored.requests.exceptions import ReadTimeout, ConnectTimeout
import requests
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


def translate_text_from_russian_to_english_with_yandex(
        *,
        russian_text: str,
        api_key: str,
) -> str:
    response = requests.get(
            'https://translate.yandex.net/api/v1.5/tr.json/translate',
            params={'key': api_key,
                    'text': russian_text,
                    'lang': 'ru-en'
                    })
    json_dict = json.loads(response.text)
    full_phrase_translated = json_dict['text'][0]

    full_phrase_translated = full_phrase_translated.lower().replace('bisque',
                                                                    'soup')
    full_phrase_translated = re.sub(r'without (\w+)', '',
                                    full_phrase_translated)
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
            original_utterance=translate_text_from_russian_to_english_with_yandex(
                    russian_text=yandex_request.command,
                    api_key=os.getenv('YandexTranslate'),
            ),
    )  # type: YandexRequest

    if translated_yandex_request.original_utterance == 'Error: timeout':
        translated_yandex_request = replace(
                translated_yandex_request,
                error='timeout')

    return translated_yandex_request
