# coding: UTF-8

__author__ = 'Benson'
import urllib.request
import urllib.parse
import urllib.error
from queue import Queue
from time import time
from API import API
import json
from make_or_queries import make_or_queries
from make_or_auid_queries import make_or_auid_queries

# 判断标识符是Id还是AuId
# 输入：API的response, expr = 'Id=%d' % Id
# 输出：如果是Id,返回True,如果是AuId，返回False
def isId(response):
    entities = response['entities']
    for entity in entities:
        if 'Ti' in entity:
            return True
    return False


# API的count参数和attr参数
COUNT = 1000000
ATTR = 'Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId'
api = API()


# 通过AuId写的论文找出AuId的机构
def findAfId(AuId, response):
    entities = response['entities']
    AfIdSet = set()
    for entity in entities:
        AA = entity['AA']
        for aa in AA:
            if aa['AuId'] == AuId:
                if 'AfId' in aa:
                    AfIdSet.add(aa['AfId'])
                break
    return AfIdSet


# 找出论文的引用
def findRId(paper):
    RIdSet = set()
    if 'RId' in paper:
        RIdSet = set(paper['RId'])
    return RIdSet

# 找出paper的JId,CId,FId,AuId的集合,即不包含RId
def nextNodes_except_RId(paper):
    nodes = set()
    if 'J' in paper:
        JId = paper['J']['JId']
        nodes.add(JId)
    if 'C' in paper:
        CId = paper['C']['CId']
        nodes.add(CId)
    if 'F' in paper:
        FIds = [f['FId'] for f in paper['F']]
        nodes.update(set(FIds))
    if 'AA' in paper:
        AA = paper['AA']
        AuIds = [aa['AuId'] for aa in AA]
        nodes.update(set(AuIds))
    return nodes

# 生成URL
def genURL(expr, attr,count):
    params = urllib.parse.urlencode({
        # Request parameters
        'expr': expr,
        'model': 'latest',
        'attributes': attr,
        'count': '%d' % count,
        'offset': '0',
        'subscription-key': 'f7cc29509a8443c5b3a5e56b0e38b5a6',
        })
    url = 'http://oxfordhk.azure-api.net/academic/v1.0/evaluate?%s' % params
    return url

# 将响应的字节型数据转换为字典
def convertToDict(response):
    return json.loads(response.decode('utf-8'))

# 找路径的主函数 未写完 需要补充和优化
def searchPath(left, right):
    # left为左边的标识符, 类型为int64
    # right为右边的标识符, 类型为int64

    global api
    # 判断两个标识符是Id还是AuId
    # 建立left的URL
    # url_left = genURL(expr='Or(Id=%d,Id=%d)' % (left, right) ,attr='Id,Ti,AA.AuId,F.FId,J.JId,C.CId,RId',count=COUNT)
    # # 建立right的URL
    # url_right = genURL(expr='Id=%d' % right, attr='Id,Ti,AA.AuId,F.FId,J.JId,C.CId',count=COUNT)

    # urls = [url_left, url_right]
    url= genURL(expr='Or(Id=%d,Id=%d)' % (left, right) ,attr='Id,Ti,AA.AuId,F.FId,J.JId,C.CId,RId',count=COUNT)
    result = api.get(url).getvalue()
    # 从result中提取出响应
    response = convertToDict(result)
    entities = response['entities']
    for entity in entities:
        if entity['Id'] == left:
            response_left = { 'entities' : [entity] }
        if entity['Id'] == right:
            response_right = { 'entities' : [entity] }
    # print(response_left,'\n', response_right)

    leftIsId = isId(response_left)
    rightIsId = isId(response_right)

    # print('leftIsId:',leftIsId)
    # print('rightIsId:',rightIsId)

    # 需要返回的路径集合
    paths = []

    # 如果left和right都是AuId
    if (not leftIsId) and (not rightIsId):
        # url for 返回左边的作者写的所有论文的信息
        url_left = genURL(expr='Composite(AA.AuId=%d)' % left, attr='Id,RId,AA.AuId,AA.AfId',count=COUNT)

        # url for 返回右边的作者写的所有论文的信息
        url_right = genURL(expr='Composite(AA.AuId=%d)' % right, attr='Id,AA.AuId,AA.AfId', count=COUNT)

        # url for 找出left与right共同写的论文的Id
        exprTmp = 'And(Composite(AA.AuId=%d),Composite(AA.AuId=%d))' % (left, right)
        url3 = genURL(expr=exprTmp, attr='Id', count=COUNT)

        # 异步API
        urls = [url_left, url_right, url3]
        result = api.multi_get(urls)
        result_dict = dict(result)

        # 提取出响应
        response_left = convertToDict(result_dict[url_left].getvalue())
        response_right = convertToDict(result_dict[url_right].getvalue())
        response_url3 = convertToDict(result_dict[url3].getvalue())

        # 找出左边作者的机构
        leftAfIdSet = findAfId(left, response_left)

        # 找出右边作者的机构
        rightAfIdSet = findAfId(right, response_right)

        # 此时1-hop的情况不存在

        #  找出 2-hop 路径
        # 找出left与right共同写的论文
        entities = response_url3['entities']
        for paper in entities:
            # 将中间点是论文的路径加入结果集合中
            pathTmp = [left, paper['Id'], right]
            paths.append(pathTmp)

        # 找出left与right共同的机构
        intersec_Af = leftAfIdSet & rightAfIdSet

        # 将中间点是机构的路径加入结果集合
        for af in intersec_Af:
            pathTmp = [left, af, right]
            paths.append(pathTmp)

        #  找出 3-hop 路径

        # 求出右边作者写的所有论文Id的集合
        rightPaperSet = set()
        entities = response_right['entities']
        for entity in entities:
            try:
                rightPaperSet.add(entity['Id'])
            except Exception:
                pass

        # 检查左边作者的论文的引用是否在rightPaperSet中，如果在，则将路径加入结果集合
        entities = response_left['entities']
        for entity in entities:
            try:
                for rid in entity['RId']:
                    if rid in rightPaperSet:
                        pathTmp = [left, entity['Id'], rid, right]
                        paths.append(pathTmp)
            except Exception:
                pass

    # 如果left是AuId，right是Id
    if (not leftIsId) and rightIsId:

        # url for 返回left写的所有论文的信息
        url_left = genURL(expr='Composite(AA.AuId=%d)' % left, attr=ATTR,count=COUNT)
        # url for 返回right的所有信息
        # url_right = genURL(expr='Id=%d' % right, attr=ATTR, count=COUNT)
        # url for 找出引用了right标识符的论文
        exprTmp = expr = 'RId=%d' % right
        url3 = genURL(exprTmp, attr='Id', count=COUNT)

        urls = [url_left, url3]
        result = api.multi_get(urls)
        result_dict = dict(result)
        # 提取出响应
        response_left = convertToDict(result_dict[url_left].getvalue())
        response_url3 = convertToDict(result_dict[url3].getvalue())

        # 返回左边的作者写的所有论文的信息
        left_papers = response_left['entities']  # 左边作者写的所有论文

        # 返回右边的论文的所有信息
        right_paper = response_right['entities'][0]

        # 找出 1-hop 路径
        for paper in left_papers:
            try:
                if paper['Id'] == right:
                    paths.append([left, right])
                    break
            except Exception:
                pass

        # 找出 2-hop 路径
        for paper in left_papers:
            RId = paper['RId']
            for rid in RId:
                if right == rid:
                    pathTmp = [left, paper['Id'], right]
                    paths.append(pathTmp)
                    break

        # 找出 3-hop 路径

        # 找出形式为 Author -> paper -> journal -> paper 的路径
        if 'J' in right_paper:
            # 找出右边论文的journal
            rightJId = right_paper['J']['JId']
            # 遍历左边作者的所有论文
            for paper in left_papers:
                if 'J' in paper:
                    paperJId = paper['J']['JId']
                    # 符合条件，路径加入结果集合
                    if paperJId == rightJId:
                        pathTmp = [left, paper['Id'], paperJId, right]
                        paths.append(pathTmp)

        # 找出形式为 Author -> paper -> conference -> paper 的路径
        if 'C' in right_paper:
            # 找出右边论文的conference
            rightCId = right_paper['C']['CId']
            for paper in left_papers:
                if 'C' in paper:
                    # C.CId
                    paperCId = paper['C']['CId']
                    # 符合条件的路径加入结果集合
                    if paperCId == rightCId:
                        pathTmp = [left, paper['Id'], paperCId, right]
                        paths.append(pathTmp)

        # 找出形式为 Author -> paper -> field -> paper 的路径
        if 'F' in right_paper:
            # 找出右边论文的field
            rightFIds = set((field['FId'] for field in right_paper['F']))
            # 遍历left写的所有论文
            for paper in left_papers:
                if 'F' in paper:
                    # 找出左边论文的field
                    paperFIds = [field['FId'] for field in paper['F']]
                    # 求左边论文与右边论文的field的交集
                    interSec = rightFIds & set(paperFIds)
                    # 路径加入paths集合
                    if interSec:
                        for fid in interSec:
                            pathTmp = [left, paper['Id'], fid, right]
                            paths.append(pathTmp)

        if 'AA' in right_paper:
            # 找出右边论文的作者
            AA = right_paper['AA']
            rightAuIds = [Au['AuId'] for Au in AA]
            rightAuIdsSet = set(rightAuIds)

            # 找出形式为 Author -> paper -> Author -> paper 的路径
            # 遍历left写的所有论文
            for paper in left_papers:
                if 'AA' in paper:
                    # 找出左边论文的作者Id
                    paperAuIds = [Au['AuId'] for Au in paper['AA']]
                    # 求左边论文与右边论文的作者的交集
                    interSec = rightAuIdsSet & set(paperAuIds)
                    for AuId in interSec:
                        pathTmp = [left, paper['Id'], AuId, right]
                        paths.append(pathTmp)

            # 找出形式为 Author -> Affiliation -> Author -> paper 的路径
            # 找出left属于的机构
            leftAfIds = findAfId(left, response_left)
            # 生成具有OR嵌套的AuId字符串列表
            or_queries = make_or_auid_queries(rightAuIds)

            # 生成expr的参数等于or_queries的元素的URL列表
            urls_AuIds = []
            for expr in or_queries:
                urlTmp = genURL(expr, 'AA.AuId,AA.AfId', COUNT)
                urls_AuIds.append(urlTmp)

            if urls_AuIds:
                result = api.multi_get(urls_AuIds)

                # 获取right的Authors的机构,并与left的机构比较，符合条件的路径加入paths
                for url, response in result:
                    # 提取出响应
                    response = convertToDict(response.getvalue())
                    entities = response['entities']
                    # 由于用以下方法找到的路径可能会出现重复，所以先存储在集合里，然后在加进paths
                    # 满足条件的路径集合
                    paths_fulfil = set()
                    for paper in entities:
                        if 'AA' in paper:
                            AA = paper['AA']
                            for aa in AA:
                                if 'AuId' in aa and 'AfId' in aa:
                                    if aa['AuId'] in rightAuIds and aa['AfId'] in leftAfIds:
                                        paths_fulfil.add((left, aa['AfId'], aa['AuId'], right))
                    for path in paths_fulfil:
                        paths.append(list(path))

        # 找出形式为 Author -> paper -> paper -> paper 的路径
        # 找出引用了right标识符的论文Id
        entities = response_url3['entities']
        Ids_Quote_Right = [paper['Id'] for paper in entities]
        Ids_Quote_Right = set(Ids_Quote_Right)

        for paper in left_papers:
            # 论文的RId集合
            RIdSet = findRId(paper)
            # 找集合的交集
            interSec = RIdSet & Ids_Quote_Right
            # 符合条件的路径加进paths中
            for Id in interSec:
                pathTmp = [left, paper['Id'], Id, right]
                paths.append(pathTmp)

    # left是paper,right是Author
    if leftIsId and not rightIsId:

        # url for 返回left的信息
        # url_left = genURL(expr='Id=%d' % left, attr='Id,AA.AuId,F.FId,J.JId,C.CId,RId', count=COUNT)
        # url for 返回right写的所有论文信息
        url_right = genURL(expr='Composite(AA.AuId=%d)' % right, attr=ATTR, count=COUNT)

        urls = [url_right]
        result = api.multi_get(urls)
        result_dict = dict(result)
        # 提取出响应
        response_right = convertToDict(result_dict[url_right].getvalue())

        # 返回left的所有信息
        leftPaper = response_left['entities'][0]

        # 返回right写的所有论文信息
        right_papers = response_right['entities']

        # right写的论文Id
        rightPaperIds = set((paper['Id'] for paper in right_papers))

        # 找出 1-hop 的路径
        # left的作者
        AA = leftPaper['AA']
        leftAuIdSet = [aa['AuId'] for aa in AA]
        if right in leftAuIdSet:
            paths.append([left, right])

        # 找出 2-hop 的路径
        if 'RId' in leftPaper:
            # 求出left的引用
            RIdSet = leftPaper['RId']
            # 求left的引用与right写的论文的交集
            interSec = set(RIdSet) & rightPaperIds
            # 符合条件的路径加入paths
            if interSec:
                for Id in interSec:
                    pathTmp = [left, Id, right]
                    paths.append(pathTmp)

        # 找出 3-hop 的路径
        # paper -> Journal -> paper -> author
        if 'J' in leftPaper:
            leftJId =leftPaper['J']['JId']
            for paper in right_papers:
                if 'J' in paper:
                    JId = paper['J']['JId']
                    if leftJId == JId:
                        paths.append([left, JId, paper['Id'], right])

        # paper -> conference -> paper -> author
        if 'C' in leftPaper:
            leftCId = leftPaper['C']['CId']
            for paper in right_papers:
                if 'C' in paper:
                    CId = paper['C']['CId']
                    if leftCId == CId:
                        paths.append([left, CId, paper['Id'], right])

        # paper -> field -> paper -> author
        if 'F' in leftPaper:
            leftFIds = set((field['FId'] for field in leftPaper['F']))
            for paper in right_papers:
                if 'F' in paper:
                    paperFIds = [field['FId'] for field in paper['F']]
                    interSec = leftFIds & set(paperFIds)
                    for fid in interSec:
                        paths.append([left, fid, paper['Id'], right])

        # paper -> paper -> paper -> author
        # 生成具有OR嵌套的expr字符串列表，一个字符串最多包含70个Id
        leftRIds = leftPaper['RId']             # left的RId的列表
        or_queries = make_or_queries(leftRIds)

        # 生成expr参数等于or_queries的元素的URL列表
        urls_RIds = []
        for expr in or_queries:
            urlTmp = genURL(expr, 'Id,RId',COUNT)
            urls_RIds.append(urlTmp)

        if urls_RIds:
            result = api.multi_get(urls_RIds)

            # 获取left的引用的RId,并与right写的论文比较，符合条件的路径加入paths
            for url, response in result:
                # 提取出响应
                response = convertToDict(response.getvalue())
                entities = response['entities']
                for paper in entities:
                    # left的引用的RId
                    RIdsTmp = set(paper['RId'])
                    interSec = RIdsTmp & rightPaperIds
                    for node in interSec:
                        paths.append([left, paper['Id'], node, right])

        # paper -> author -> paper -> author
        if 'AA' in leftPaper:
            # 找出left的作者
            AA = leftPaper['AA']
            leftAuIds = [Au['AuId'] for Au in AA]
            leftAuIdsSet = set(leftAuIds)
            # 遍历right写的所有论文
            for paper in right_papers:
                if 'AA' in paper:
                    # 找出作者Id
                    paperAuIds = [Au['AuId'] for Au in paper['AA']]
                    interSec = leftAuIdsSet & set(paperAuIds)
                    for AuId in interSec:
                        pathTmp = [left, AuId, paper['Id'], right]
                        paths.append(pathTmp)

            # paper -> author -> affiliation -> author
            # 找出 right的机构
            rightAfIds = findAfId(right,response_right)
             # 生成具有OR嵌套的AuId字符串列表
            or_queries = make_or_auid_queries(leftAuIds)

            # 生成expr的参数等于or_queries的元素的URL列表
            urls_AuIds = []
            for expr in or_queries:
                urlTmp = genURL(expr, 'AA.AuId,AA.AfId', COUNT)
                urls_AuIds.append(urlTmp)

            if urls_AuIds:
                result = api.multi_get(urls_AuIds)

                # 获取left的Authors的机构,并right的机构比较，符合条件的路径加入paths
                for url, response in result:
                    # 提取出响应
                    response = convertToDict(response.getvalue())
                    entities = response['entities']
                    # 由于用以下方法找到的路径可能会出现重复，所以先存储在集合里，然后在加进paths
                    # 满足条件的路径集合
                    paths_fulfil = set()
                    for paper in entities:
                        if 'AA' in paper:
                            AA = paper['AA']
                            for aa in AA:
                                if 'AuId' in aa and 'AfId' in aa:
                                    if aa['AuId'] in leftAuIds and aa['AfId'] in rightAfIds:
                                        paths_fulfil.add((left, aa['AuId'], aa['AfId'],  right))
                    for path in paths_fulfil:
                        paths.append(list(path))

    # left是paper,right是paper
    if leftIsId and rightIsId:
        # url for 返回left的所有信息
        # url_left = genURL(expr='Id=%d' % left, attr='Id,AA.AuId,F.FId,J.JId,C.CId,RId',count=COUNT)
        # url for 返回right的所有信息
        # url_right = genURL(expr='Id=%d' % right, attr='Id,AA.AuId,F.FId,J.JId,C.CId,RId', count=COUNT)
        # url for 找出引用了right标识符的论文
        exprTmp = expr = 'RId=%d' % right
        url_citeRight = genURL(exprTmp, attr='Id,AA.AuId,F.FId,J.JId,C.CId', count=COUNT)

        urls = [url_citeRight]
        result = api.multi_get(urls)
        result_dict = dict(result)
        # 提取出响应
        response_citeRight = convertToDict(result_dict[url_citeRight].getvalue())

        # 返回left的所有信息
        leftPaper = response_left['entities'][0]

        # 返回right的所有信息
        rightPaper = response_right['entities'][0]

        # 返回引用了right的所有论文
        citeRight_papers = response_citeRight['entities']

        # 引用了right的所有论文的Id
        citeRight_Ids = set((paper['Id'] for paper in citeRight_papers))

        # left的引用的Id的集合
        leftRIds = set(leftPaper['RId'])

        # 返回left和right的JId, CId, FId, AuId 的集合
        leftNext = nextNodes_except_RId(leftPaper)
        rightNext = nextNodes_except_RId(rightPaper)

        # 找出 1-hop 路径
        if rightPaper['Id'] in leftRIds:
            paths.append([left,right])

        # 找出 2-hop 路径
        interSec = leftNext & rightNext
        for node in interSec:
            paths.append([left, node, right])

        # paper -> RId -> paper
        interSec = leftRIds & citeRight_Ids
        for rid in interSec:
            paths.append([left, rid, right])

        # 找出 3-hop
        # paper -> (JId,CId,FId,AuId) -> paper -> paper
        for paper in citeRight_papers:
            nextTmp = nextNodes_except_RId(paper)
            interSec = nextTmp & leftNext
            for node in interSec:
                paths.append([left, node, paper['Id'], right])

        # 生成具有OR嵌套的expr字符串列表，一个字符串最多包含70个Id
        # left的RId的列表
        leftRIds = leftPaper['RId']
        or_queries = make_or_queries(leftRIds)

        #生成expr的参数等于or_queries的元素的URL列表
        urls_RIds = []
        for expr in or_queries:
            urlTmp = genURL(expr, 'Id,AA.AuId,F.FId,J.JId,C.CId,RId', COUNT)
            urls_RIds.append(urlTmp)

        if urls_RIds:
            result = api.multi_get(urls_RIds)

            #获取left的引用的JId,CId,FId,RId,AuId,并与right的信息比较，符合条件的路径加入paths
            for url, response in result:
                # 提取出响应
                response = convertToDict(response.getvalue())
                entities = response['entities']
                for paper in entities:
                    # left的引用的JId,CId,FId,RId,AuId
                    nextTmp = nextNodes_except_RId(paper)
                    interSec = nextTmp & rightNext
                    for node in interSec:
                        paths.append([left, paper['Id'], node, right])

                    # left的引用的RId与引用right的Id的交集
                    interSec = set(paper['RId']) & citeRight_Ids
                    for node in interSec:
                        paths.append([left, paper['Id'], node, right])

    return paths


if __name__ == '__main__':
    AuId = 2145115012
    start = time()
    # id, id
    paths = searchPath(2147152912, 307743305)
    # paths = searchPath(1972106549, 2294766364)
    print('paths:')
    print(paths)
    print('num of paths:', len(paths))
    print("Elapsed time:", time()-start)
