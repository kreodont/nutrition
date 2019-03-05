import time


def timeit(target_function):
    def timed(*args, **kwargs):
        start_time = time.time()
        result = target_function(*args, **kwargs)
        end_time = time.time()
        milliseconds = (end_time - start_time) * 1000
        first_column = f'Function "{target_function.__name__}":'
        if target_function.__name__ == 'functional_nutrition_dialog':
            print('-' * 90)
        print(f'{first_column:80} {milliseconds:.1f} ms')
        if target_function.__name__ == 'functional_nutrition_dialog':
            print('-' * 90)
        return result

    return timed
