from dynamodb_functions import get_dynamo_client
import requests
import os
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


def translate_into_english(russian_phrase: str) -> str:
    response = requests.get(
            'https://translate.yandex.net/api/v1.5/tr.json/translate',
            params={
                'key' : os.getenv('YandexTranslate'),
                'text': russian_phrase,
                'lang': 'ru-en'
            },

    )
    if response.status_code == 200:
        json_dict = json.loads(response.text)
        english_phrase = json_dict['text'][0]
    else:
        print(f'Error Yandex Translate phrase "{russian_phrase}": '
              f'{response.reason}')
        return ''

    return english_phrase


def find_fdc_id(english_phrase: str, api_key):
    search_response = requests.post(
            f'https://api.nal.usda.gov/fdc/v1/search?api_key={api_key}',
            data=json.dumps({
                "generalSearchInput": english_phrase,
                'requireAllWords'   : True,
            }),
            headers={'Content-Type': 'application/json', }
    )
    try:
        result_dict = search_response.json()
    except Exception as e:
        print(f'Could not parse search response: {e}')
        return

    description_to_code_dict = {}
    max_score = 0
    for food in result_dict['foods']:
        if float(food['score']) < max_score:
            break
        max_score = float(food['score'])
        description_to_code_dict[food['fdcId']] = {
            'fdcId'    : food['fdcId'],
            'ndbNumber': food.get('ndbNumber', 'No ndb Number'),
            'name'     : food['description'],
            'data_type': food.get('dataType'),
        }

    if len(description_to_code_dict) == 0:
        print(f'No foods for {english_phrase} found')
        return
    if len(description_to_code_dict) > 1:
        print('Chose one of the options:')
        for food in description_to_code_dict.values():
            print(f"{food['fdcId']}\t\t{food['name']}\t\t\t{food['data_type']}")
        return

    return list(description_to_code_dict.values())[0]['fdcId']


def get_data_from_usda(
        russian_phrase,
        english_phrase=None,
        fdc_id=None,
        api_key='70gpTJHp6ifz0IpFX02BxzyJPZ0aStfYrfJUtY8h',
):
    if english_phrase is None:
        english_phrase = translate_into_english(russian_phrase)
        if english_phrase == '':
            return

    print(f'English: {english_phrase}')

    if fdc_id is None:
        fdc_id = find_fdc_id(english_phrase, api_key)
        if fdc_id is None:
            return

    print(f'FDC id: {fdc_id}')

    response = requests.get(
            f'https://api.nal.usda.gov/fdc/v1/{fdc_id}?api_key={api_key}',
            headers={'Content-Type': 'application/json', }
    )
    result_dict = {'portions': {}, 'nutrients': {}}
    try:
        data_dict = response.json()
    except json.decoder.JSONDecodeError:
        print(f'Cannot decode: {response.text}')
        return
    # print(data_dict['foodPortions'])
    for portion in data_dict['foodPortions']:
        portion_name = portion.get('portionDescription')
        if not portion_name:
            portion_name = portion['modifier']
        result_dict[portion_name] = {
            'grams': portion["gramWeight"],
        }
        print(f'{portion_name} {portion["gramWeight"]} g')

    print('\n\n')

    for nutrient in data_dict['foodNutrients']:
        print(f'{nutrient["nutrient"]["name"]}: '
              f'{nutrient.get("amount")} {nutrient["nutrient"]["unitName"]}')
        result_dict['nutrients'][nutrient["nutrient"]["name"]] = {
            'name': nutrient["nutrient"]["name"],
            'unit': nutrient["nutrient"]["unitName"],
            'amount': nutrient.get('amount')
        }
    return result_dict


def manually_add_food_into_dynamo_cached(
        *,
        food_name: str,
        table_name: str = 'nutrition_cache',
        calories_in_100_grams: float,
        fat: float,  # Жиры
        protein: float,  # Белки
        carbohydrate: float,  # Углеводы
        sodium: float,  # Натрий
        potassium: float,  # Калий
        saturated_fat: float,  # Насыщенные жиры
        dietary_fiber: float,  # Клетчатка (Пищевые волокна)
        sugar: float,  # Сахар
        cholesterol: float,  # Холестерол
        vitamin_a: float,  # Витамин А
        vitamin_b6: float,  # Витамин B6 (Пиридоксин)
        vitamin_b12: float,  # Витамин B12 µg = 0.000001 g
        vitamin_c: float,  # Витамин С
        vitamin_d: float,  # Витамин Д
        vitamin_e: float,  # Витамин Е
        iron: float,  # Железо
        magnesium: float,  # Магний
        water: float,  # Вода
        phosphorus: float,  # Фосфор
        zinc: float,  # Цинк
        copper: float,  # Медь
        selenium: float,  # Селен
        fluoride: float,  # Фторид
        thiamin: float,  # Тиамин (Витамин B1)
        riboflavin: float,  # Рибофлавин (Витамин B2)
        niacin: float,  # Ниацин, Витамин B3, никотиновая кислота,
        # витамин PP
        pantothenic_acid: float,  # Пантотеновая кислота (Витамин B5)
        folate: float,  # Фолат
        folic_acid: float,  # Фолиевая кислота (Витамин B9)
        fatty_acids_monounsaturated: float,  # мононенасыщенные жирные
        # кислоты (Витамин F)
        stigmasterol: float,  # Стигмастерин
        campesterol: float,  # Кампестерин
        beta_sitosterol: float,  # Бета ситостерол
        tryptophan: float,  # Триптофан
        threonine: float,  # Треонин
        isoleucine: float,  # Изолейцин
        leucine: float,  # Лейцин
        lysine: float,  # Лизин
        methionine: float,  # Метионин
        cystine: float,  # Цистин
        phenylalanine: float,  # Фенилаланин
        tyrosine: float,  # Тирозин
        valine: float,  # Валин
        arginine: float,  # Аргинин
        histidine: float,  # Гистидин
        alanine: float,  # Аланин
        aspartic_acid: float,  # Аспарагиновая кислота
        glutamic_acid: float,  # Глютаминовая кислота
        glycine: float,  # Глицин
        proline: float,  # Пролина
        serine: float,  # Серин
        alcohol: float,  # Алкоголь (этинол)
        caffeine: float,  # Кофеин
        theobromine: float,  # Теобромин
        choline: float,  # Холин (Витамин B4)
        biotin: float,  # Биотин (Витамин B7, витамин Н, коэнзим R)
        inositol: float,  # Витамин B8 (Инозитол, инозит,инозитдроретинол)
        synonims: tuple = (),
):
    parameters_dict = locals()
    del parameters_dict['synonims']
    del parameters_dict['table_name']
    # print(parameters_dict)
    existing_record = check_dynamo_cached_data(food_name, table_name=table_name)
    if 'foods' in existing_record and len(existing_record['foods']) > 0:
        print(f'There is already food "{food_name}" saved '
              f'in table {table_name}:')
        print(existing_record)
        print('You have to manually delete it first')
        return

    data_dict = {'foods': [
        {
            'food_name'            : food_name,
            'serving_qty'          : 100,
            'serving_unit'         : 'gram',
            'serving_weight_grams' : 100,
            'nf_calories'          : calories_in_100_grams,
            'nf_total_fat'         : fat,
            'nf_saturated_fat'     : saturated_fat,
            'nf_cholesterol'       : cholesterol,
            'nf_sodium'            : sodium,
            'nf_total_carbohydrate': carbohydrate,
            'nf_dietary_fiber'     : dietary_fiber,
            'nf_sugars'            : sugar,
            'nf_protein'           : protein,
            'nf_potassium'         : potassium,
            'vitamin_a'            : vitamin_a,
            'vitamin_b6'           : vitamin_b6,
            'vitamin_b12'          : vitamin_b12,
            'alanine'              : alanine,
        },
    ]}

    data_dict['foods'][0].update(parameters_dict)
    dynamo_client = get_dynamo_client(lambda_mode=False)
    print(f'Writing "{food_name}" into database')
    dynamo_client.put_item(TableName=table_name,
                           Item={
                               'initial_phrase': {
                                   'S': food_name,
                               },
                               'response'      : {
                                   'S': json.dumps(data_dict),
                               }})
    # print(data_dict)
    for synonim in synonims:
        print(f'Updating synonim {synonim}')
        manually_add_food_into_dynamo_cached(
                food_name=synonim,
                calories_in_100_grams=calories_in_100_grams,
                fat=fat,
                saturated_fat=saturated_fat,
                cholesterol=cholesterol,
                sodium=sodium,
                carbohydrate=carbohydrate,
                sugar=sugar,
                potassium=potassium,
                protein=protein,
                dietary_fiber=dietary_fiber,
                vitamin_a=vitamin_a,
                vitamin_b6=vitamin_b6,
                vitamin_b12=vitamin_b12,
                vitamin_c=vitamin_c,
                vitamin_d=vitamin_d,
                vitamin_e=vitamin_e,
                iron=iron,
                magnesium=magnesium,
                water=water,
                phosphorus=phosphorus,
                zinc=zinc,
                copper=copper,
                selenium=selenium,
                fluoride=fluoride,
                thiamin=thiamin,
                riboflavin=riboflavin,
                niacin=niacin,
                pantothenic_acid=pantothenic_acid,
                folate=folate,
                folic_acid=folic_acid,
                fatty_acids_monounsaturated=fatty_acids_monounsaturated,
                stigmasterol=stigmasterol,
                campesterol=campesterol,
                beta_sitosterol=beta_sitosterol,
                tryptophan=tryptophan,
                threonine=threonine,
                isoleucine=isoleucine,
                leucine=leucine,
                lysine=lysine,
                methionine=methionine,
                cystine=cystine,
                phenylalanine=phenylalanine,
                tyrosine=tyrosine,
                valine=valine,
                arginine=arginine,
                histidine=histidine,
                alanine=alanine,
                aspartic_acid=aspartic_acid,
                glutamic_acid=glutamic_acid,
                glycine=glycine,
                proline=proline,
                serine=serine,
                alcohol=alcohol,
                caffeine=caffeine,
                theobromine=theobromine,
                choline=choline,
                biotin=biotin,
                inositol=inositol,
                synonims=(),  # important to leave empty to prevent endless
                # recursion
        )


print(get_data_from_usda('Кофе'))
# print(list(check_dynamo_cached_data('морковь')['foods'][0].keys()))
# print(check_dynamo_cached_data('сливочное масло'))
# delete_dymamo_data('сливочным маслом')
# manually_add_food_into_dynamo_cached(
#         food_name='сливочным маслом',
#         calories_in_100_grams=717,
#         fat=81,
#         saturated_fat=51,
#         cholesterol=0.215,
#         sodium=0.011,
#         carbohydrate=0.1,
#         sugar=0.1,
#         potassium=0.024,
#         protein=0,
#         dietary_fiber=0,
#         vitamin_a=0,
#         vitamin_b6=0,
#         vitamin_b12=0,
#         vitamin_c=0,
#         vitamin_d=0,
#         vitamin_e=0,
#         iron=0,
#         magnesium=0,
#         water=0,
#         phosphorus=0,
#         zinc=0,
#         copper=0,
#         selenium=0,
#         fluoride=0,
#         thiamin=0,
#         riboflavin=0,
#         niacin=0,
#         pantothenic_acid=0,
#         folate=0,
#         folic_acid=0,
#         fatty_acids_monounsaturated=0,
#         stigmasterol=0,
#         campesterol=0,
#         beta_sitosterol=0,
#         tryptophan=0,
#         threonine=0,
#         isoleucine=0,
#         leucine=0,
#         lysine=0,
#         methionine=0,
#         cystine=0,
#         phenylalanine=0,
#         tyrosine=0,
#         valine=0,
#         arginine=0,
#         histidine=0,
#         alanine=0,
#         aspartic_acid=0,
#         glutamic_acid=0,
#         glycine=0,
#         proline=0,
#         serine=0,
#         alcohol=0,
#         caffeine=0,
#         theobromine=0,
#         choline=0,
#         biotin=0,
#         inositol=0,
#         # synonims=('сливочное масло', 'сливочным маслом')
# )
