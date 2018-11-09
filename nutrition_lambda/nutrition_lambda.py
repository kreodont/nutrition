from botocore.vendored import requests
import json
import os


def nutrition_lambda(event: dict, context: dict) -> int:
    """
    Gets nutrition data from https://developer.nutritionix.com

    :param event: input parameters
        event['product'] - product name in English

    :param context: indicates if it runs in AWS environment
    :return: calories number in 100 g of the product. Returns -1 if product not found
    """

    if context:
        x_app_id = ''
        x_app_key = ''
    else:
        x_app_id = os.environ['NUTRITIONIXID']
        x_app_key = os.environ['NUTRITIONIXKEY']

    event.setdefault('product', '')
    print(event)
    if not event['product']:
        return -1

    request_data = {'line_delimited': False,
                    'query': event['product'],
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
        return -1

    print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')))


if __name__ == '__main__':
    nutrition_lambda({'product': 'vegetable soup'}, {})
