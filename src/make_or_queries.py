# coding: UTF-8


# 函数的输入是一个列表[Id1, Id2, Id3, ....]
# 因为expr长度有限制,最长为1800个字符，所以一个OR嵌套的字符串里的Id数量限定最多95个
# 函数输出就是嵌套的字符串的列表,输出是列表的原因是输入的Id列表里的Id数目可能大于95个
def make_or_queries(ids):
    if len(ids)>1:
        return [make_an_or_query('Id', map(str, chunk), len(chunk)) for chunk in chunks(ids, 70)]
    else:
        return ['Id=%d' % ids[0]]


def chunks(l, n):
    '''yield successive n-sized chunks from l'''
    for i in range(0, len(l), n):
        yield l[i : i + n]


def make_an_or_query(field_name, ids, num):
    first_id = next(ids)
    begin = 'Or(' + field_name + '=' + first_id
    between = ',Or(' + field_name + '='
    end = ',' + field_name + '=' + first_id + ')' * num
    return ''.join((begin, between, between.join(ids), end))
