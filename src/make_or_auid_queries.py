# coding:UTF-8


# 函数的输入是一个列表[AuId1, AuId2, AuId3, ...]
# 因为expr长度有限制,最长为1800个字符，所以一个OR嵌套的字符串里的AuId数量限定最多35个
# 函数输出就是嵌套的字符串的列表,输出是列表的原因是输入的AuId列表里的AuId数目可能大于35个
def make_or_auid_queries(AuIds):
    if AuIds:
        if len(AuIds)>1:
            return [make_an_or_query('AA.AuId', map(str, chunk), len(chunk)) for chunk in chunks(AuIds, 35)]
        else:
            return ['Composite(AA.AuId=%d)' % AuIds[0]]
    else:
        return []


def chunks(l, n):
    '''yield successive n-sized chunks from l'''
    for i in range(0, len(l), n):
        yield l[i : i + n]


def make_an_or_query(field_name, ids, num):
    first_id = next(ids)
    begin = 'Or(' + 'Composite('+field_name + '=' + first_id
    between = '),Or(' + 'Composite(' + field_name + '='
    end = '),' + 'Composite(' + field_name + '=' + first_id + ')' + ')' * num
    return ''.join((begin, between, between.join(ids), end))
