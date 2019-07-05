# import itertools
import typing


def func1(*, parameter):
    print(parameter)
    return None


def func2(*, parameter):
    print(parameter)
    return None


def func3(*, parameter):
    print(parameter)
    return None


def func4(*, parameter):
    print(parameter)
    return 'Not none'


def func5(*, parameter):
    print(parameter)
    return None


func_list = (func1, func2, func3, func4, func5)


def return_the_first_result_from_the_list_of_functions(
        *,
        functions_list: typing.Tuple[typing.Callable, ...],
        debug_mode: bool = False,
        **parameters):

    for f in functions_list:
        result = f(**parameters)
        if result:
            if debug_mode:
                print(f'Function {f.__name__} returned result the first')
            return result

        if debug_mode:
            print(f'Function {f.__name__} did not return result')
