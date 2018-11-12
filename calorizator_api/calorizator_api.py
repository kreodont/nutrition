from botocore.vendored import requests
import json


def calorizator_api(event: dict, context: dict) -> int:
    """
    Gets nutrition data from http://www.calorizator.ru/search/load
    Returns nutrition in 100 g of this product.

    :param event: input parameters
        event['product'] - product name

    :param context: indicates if it runs in AWS environment
    :return: calories number in 100 g of the product. Returns -1 if product not found
    """
    if context:
        pass

    event.setdefault('product', '')
    print(event)
    if not event['product']:
        return -1

    request_data = {'search': event['product']
                    }

    response = requests.post('http://www.calorizator.ru/search/load',
                             # data='{search: %s}' % event['product'],
                             data=json.dumps(request_data),
                             headers={
                                 'content-type': 'text/html',
                                 'charset': 'utf-8',
                             }
                             )

    if response.status_code != 200:
        print(f'Exception: {response.text}')
        return -1
    print(response.text)
    return 0
    # print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')))


if __name__ == '__main__':
    print(calorizator_api({'product': 'snickers'}, {}))
