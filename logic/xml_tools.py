from datetime import datetime


def get_text_value(tree, key):
    if tree.find(key) is None:
        return
    if tree.find(key).text is None:
        return
    return tree.find(key).text.replace('\"', '')


def get_date_value(tree, key):
    if tree.find(key) is None:
        return
    if tree.find(key).text is None:
        return
    try:
        return datetime.strptime(tree.find(key).text, '%d.%m.%Y %H:%M:%S')
    except ValueError:
        return


def get_float_value(tree, key):
    if tree.find(key) is None:
        return 0
    return float(tree.find(key).text.replace('.', '').replace(',', '.').replace(' ', ''))


def get_float_value_with_dot(tree, key):
    if tree.find(key) is None:
        return 0
    if tree.find(key).text[-1] == '-':
        return -float(tree.find(key).text[:-1])
    else:
        return float(tree.find(key).text)
