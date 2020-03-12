from dynamodb_functions import get_dynamo_client
import json


def check_dynamo_cached_data(key_string: str, table_name='nutrition_cache'):
    dynamo_client = get_dynamo_client(lambda_mode=False)
    bulb = dynamo_client.get_item(
            TableName=table_name,
            Key={'initial_phrase': {'S': key_string}})
    if ('Item' not in bulb or
            'response' not in bulb['Item'] or
            'S' not in bulb['Item']['response']):
        return {}

    return json.loads(bulb['Item']['response']['S'])


def delete_dymamo_data(key_string: str, table_name='nutrition_cache'):
    dynamo_client = get_dynamo_client(lambda_mode=False)
    response = dynamo_client.delete_item(
            TableName=table_name,
            Key={'initial_phrase': {'S': key_string}})

    print(response)


def manually_add_food_into_dynamo_cached(
        *,
        food_name: str,
        table_name: str = 'nutrition_cache',
        calories_in_100_grams: float,
        fat: float,             # Жиры
        protein: float,         # Белки
        carbohydrate: float,    # Углеводы
        sodium: float,          # Натрий
        potassium: float,       # Калий
        saturated_fat: float,   # Насыщенные жиры
        dietary_fiber: float,   # Клетчатка (Пищевые волокна)
        sugar: float,           # Сахар
        cholesterol: float,     # Холестерол
        vitamin_a: float,       # Витамин А
        vitamin_b6: float,      # Витамин B6 (Пиридоксин)
        vitamin_b12: float,     # Витамин B12 µg = 0.000001 g
        vitamin_c: float,       # Витамин С
        vitamin_d: float,       # Витамин Д
        vitamin_e: float,       # Витамин Е
        iron: float,            # Железо
        magnesium: float,       # Магний
        water: float,           # Вода
        phosphorus: float,      # Фосфор
        zinc: float,            # Цинк
        copper: float,          # Медь
        selenium: float,        # Селен
        fluoride: float,        # Фторид
        thiamin: float,         # Тиамин (Витамин B1)
        riboflavin: float,      # Рибофлавин (Витамин B2)
        niacin: float,          # Ниацин, Витамин B3, никотиновая кислота,
        # витамин PP
        pantothenic_acid: float,  # Пантотеновая кислота (Витамин B5)
        folate: float,          # Фолат
        folic_acid: float,      # Фолиевая кислота
        fatty_acids_total_monounsaturated: float,  # мононенасыщенные жирные
        # кислоты
        stigmasterol: float,    # Стигмастерин
        campesterol: float,     # Кампестерин
        beta_sitosterol: float,  # Бета ситостерол
        tryptophan: float,      # Триптофан
        threonine: float,       # Треонин
        isoleucine: float,      # Изолейцин
        leucine: float,         # Лейцин
        lysine: float,          # Лизин
        methionine: float,      # Метионин
        cystine: float,         # Цистин
        phenylalanine: float,   # Фенилаланин
        tyrosine: float,        # Тирозин
        valine: float,          # Валин
        arginine: float,        # Аргинин
        histidine: float,       # Гистидин
        alanine: float,         # Аланин
        aspartic_acid: float,   # Аспарагиновая кислота
        glutamic_acid: float,   # Глютаминовая кислота
        glycine: float,         # Глицин
        proline: float,         # Пролина
        serine: float,          # Серин
        alcohol: float,         # Алкоголь (этинол)
        caffeine: float,        # Кофеин
        theobromine: float,     # Теобромин
        choline: float,         # Холин (Витамин B4)
        biotin: float,          # Биотин (Витамин B7, витамин Н, коэнзим R)

        synonims: tuple = (),
):
    existing_record = check_dynamo_cached_data(food_name, table_name=table_name)
    if 'foods' in existing_record and len(existing_record['foods']) > 0:
        print(f'There is already food "{food_name}" saved '
              f'in table {table_name}')
        print(existing_record)
        print('You have to manually delete it first')
        return

    data_dict = {'foods': [
        {
            'food_name': food_name,
            'serving_qty': 100,
            'serving_unit': 'gram',
            'serving_weight_grams': 100,
            'nf_calories': calories_in_100_grams,
            'nf_total_fat': fat,
            'nf_saturated_fat': saturated_fat,
            'nf_cholesterol': cholesterol,
            'nf_sodium': sodium,
            'nf_total_carbohydrate': carbohydrate,
            'nf_dietary_fiber': dietary_fiber,
            'nf_sugars': sugar,
            'nf_protein': protein,
            'nf_potassium': potassium,
            'vitamin_a': vitamin_a,
            'vitamin_b6': vitamin_b6,
            'vitamin_b12': vitamin_b12,
            'alanine': alanine,
        },
    ]}

    print(data_dict)
    for synonim in synonims:
        print(f'Updating synonim {synonim}')
        manually_add_food_into_dynamo_cached(
                food_name=synonim,
                table_name=table_name,
                calories_in_100_grams=calories_in_100_grams,
                fat=fat,
                carbohydrate=carbohydrate,
                sodium=sodium,
                potassium=potassium,
                saturated_fat=saturated_fat,
                dietary_fiber=dietary_fiber,
                sugar=sugar,
                cholesterol=cholesterol,
                alanine=alanine,
                alcohol=alcohol,
                synonims=(),  # important to leave empty to prevent endless
                # recursion
        )


# print(list(check_dynamo_cached_data('морковь')['foods'][0].keys()))
# print(check_dynamo_cached_data('масло'))
manually_add_food_into_dynamo_cached(
        food_name='масло',
        calories_in_100_grams=717,
        fat=81,
        saturated_fat=51,
        cholesterol=0.215,
        sodium=0.011,
        carbohydrate=0.1,
        sugar=0.1,
        potassium=0.024,

        synonims=('сливочное масло', 'сливочным маслом')
)
