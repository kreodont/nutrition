

def nutrition_lambda(event: dict, context: dict) -> int:
    """
    Gets nutrition data from https://developer.nutritionix.com
    :param event: input parameters
        event['product'] - product name in English

    :param context: indicates if it runs in AWS environment
    :return: calories number in 100 g of the product
    """
    lambda_mode = bool(context)  # type: bool
    print(event)

    return -1


if __name__ == '__main__':
    nutrition_lambda({}, {})
