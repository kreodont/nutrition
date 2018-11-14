from botocore.vendored import requests
import json
import os


def nutritionix_lambda(event: dict, context: dict) -> dict:
    """
    Gets nutrition data from https://developer.nutritionix.com

    :param event: input parameters
        event['product'] - product name in English

    :param context: indicates if it runs in AWS environment
    :return: calories number in 100 g of the product. Returns -1 if product not found
    """

    x_app_id = os.environ['NUTRITIONIXID']
    x_app_key = os.environ['NUTRITIONIXKEY']

    event.setdefault('phrase', '')
    event.setdefault('debug', bool(context))  # Debug mode in AWS and not in local

    print(event)

    if not event['phrase']:
        return {}

    request_data = {'line_delimited': False,
                    'query': event['phrase'],
                    'timezone': "Europe/Moscow",
                    'use_branded_foods': False,
                    'use_raw_foods': False,
                    }

    response = requests.post('https://trackapi.nutritionix.com/v2/natural/nutrients',
                             data=json.dumps(request_data),
                             headers={'content-type': 'application/json',
                                      'x-app-id': x_app_id,
                                      'x-app-key': x_app_key},
                             )

    if response.status_code != 200:
        print(f'Exception: {response.text}')
        return {}

    try:
        response_json = response.json()
        if event['debug']:
            print(json.dumps(response_json, sort_keys=True, indent=4, separators=(',', ': ')))
        return response_json
    except json.JSONDecodeError:
        return {}


if __name__ == '__main__':
    print(nutritionix_lambda({'phrase': 'Potato puree, 300 g'}, {}))
