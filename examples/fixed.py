"""示例修复：取消任意表达式求值，只接受两个数和明确运算符。"""
import operator


def add_item(item, items=None):
    if items is None:
        items = []
    items.append(item)
    return items


def parse_number(text):
    # 无效输入向调用者抛出 ValueError，避免与合法的 0 混淆。
    return int(text)


def calculate(left, operation, right):
    operations = {'+': operator.add, '-': operator.sub,
                  '*': operator.mul, '/': operator.truediv}
    if operation not in operations:
        raise ValueError('不支持的运算符')
    return operations[operation](float(left), float(right))
