"""故意保留问题的审查样本。请勿用于生产。"""


def add_item(item, items=[]):
    items.append(item)
    return items


def parse_number(text):
    try:
        return int(text)
    except:
        return 0


def calculate(expression):
    return eval(expression)
