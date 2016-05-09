# coding: UTF-8

__author__ = 'Benson'
import urllib.request
import urllib.parse
import urllib.error
from queue import Queue
from time import time
from API import API
import json

# 判断标识符是Id还是AuId
# 输入：API的response, expr = 'Id=%d' % Id
# 输出：如果是Id,返回True,如果是AuId，返回False
def isId(response):
    entities = response['entities']
    for entity in entities:
        if 'Ti' in entity.keys():
            return True
    return False


# API的count参数和attr参数
COUNT = 1000000
ATTR = 'Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId'


# 通过AuId写的论文找出AuId的机构
def findAfId(AuId, response):
    entities = response['entities']
    AfIdSet = set()
    for entity in entities:
        AA = entity['AA']
        for aa in AA:
            if aa['AuId'] == AuId:
                if 'AfId' in aa.keys():
                    AfIdSet.add(aa['AfId'])
                break
    return AfIdSet


# 找出论文的引用
def findRId(paper):
    RIdSet = set()
    if 'RId' in paper.keys():
        RIdSet = set(paper['RId'])
    return RIdSet

# 找出paper的JId,CId,FId,AuId的集合,即不包含RId
def nextNodes_except_RId(paper):
    nodes = set()
    if 'J' in paper.keys():
        JId = paper['J']['JId']
        nodes.add(JId)
    if 'C' in paper.keys():
        CId = paper['C']['CId']
        nodes.add(CId)
    if 'F' in paper.keys():
        FIds = [f['FId'] for f in paper['F']]
        nodes = nodes | set(FIds)
    if 'AA' in paper.keys():
        AA = paper['AA']
        AuIds = [aa['AuId'] for aa in AA]
        nodes = nodes | set(AuIds)
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

# 转换为字典
def convertToDict(response):
    return json.loads(response.decode('utf-8'))

# 找路径的主函数 未写完 需要补充和优化
def searchPath(left, right):
    # left为左边的标识符, 类型为int64
    # right为右边的标识符, 类型为int64

    # 判断两个标识符是Id还是AuId
    # 建立left的URL
    url_left = genURL(expr='Id=%s' % left, attr='Id,Ti', count=1)
    # 建立right的URL
    url_right = genURL(expr='Id=%s' % right, attr='Id,Ti', count=1)

    urls = [url_left, url_right]
    api = API()
    q = Queue()
    # 调用异步API
    api.multi_get_async(urls, lambda x: q.put_nowait(x))
    result = q.get()
    result_dict = dict(result)
    # 从result中提取出响应
    response_left = convertToDict(result_dict[url_left].getvalue())
    response_right = convertToDict(result_dict[url_right].getvalue())
    # print(response_left,'\n', response_right)

    if isId(response_left):
        leftIsId = True   # 左边的标识符是Id
    else:
        leftIsId = False  # 左边的标识符是AuId

    if isId(response_right):
        rightIsId = True   # 右边的标识符是Id
    else:
        rightIsId = False  # 右边的标识符是AuId

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

        # url for 找出left与right共同写的论文
        exprTmp = 'And(Composite(AA.AuId=%d),Composite(AA.AuId=%d))' % (left, right)
        url3 = genURL(expr=exprTmp, attr='Id', count=COUNT)

        # 异步API
        urls = [url_left, url_right, url3]
        api = API()
        q = Queue()
        api.multi_get_async(urls, lambda x: q.put_nowait(x))
        result = q.get()
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
            if 'Id' in entity.keys():
                rightPaperSet.add(entity['Id'])

        # 检查左边作者的论文的引用是否在rightPaperSet中，如果在，则将路径加入结果集合
        entities = response_left['entities']
        for entity in entities:
            if 'RId' in entity.keys():
                for rid in entity['RId']:
                    if rid in rightPaperSet:
                        pathTmp = [left, entity['Id'], rid, right]
                        paths.append(pathTmp)

    # 如果left是AuId，right是Id
    if (not leftIsId) and rightIsId:

        # url for 返回left写的所有论文的信息
        url_left = genURL(expr='Composite(AA.AuId=%d)' % left, attr=ATTR,count=COUNT)
        # url for 返回right的所有信息
        url_right = genURL(expr='Id=%d' % right, attr=ATTR, count=COUNT)
        # url for 找出引用了right标识符的论文
        exprTmp = expr = 'RId=%d' % right
        url3 = genURL(exprTmp, attr=ATTR, count=COUNT)

        urls = [url_left, url_right, url3]
        api = API()
        q = Queue()
        # 异步API
        api.multi_get_async(urls, lambda x: q.put_nowait(x))
        result = q.get()
        result_dict = dict(result)
        # 提取出响应
        response_left = convertToDict(result_dict[url_left].getvalue())
        response_right = convertToDict(result_dict[url_right].getvalue())
        response_url3 = convertToDict(result_dict[url3].getvalue())


        # 返回左边的作者写的所有论文的信息
        left_papers = response_left['entities']  # 左边作者写的所有论文

        # 返回右边的论文的所有信息
        right_paper = response_right['entities'][0]


        # 找出 1-hop 路径
        for paper in left_papers:
            if 'Id' in paper.keys():
                if paper['Id'] == right:
                    paths.append([left, right])
                    break

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
        if 'J' in right_paper.keys():
            # 找出右边论文的journal
            rightJId = right_paper['J']['JId']
            # 遍历左边作者的所有论文
            for paper in left_papers:
                if 'J' in paper.keys():
                    paperJId = paper['J']['Id']
                    # 符合条件，路径加入结果集合
                    if paperJId == rightJId:
                        pathTmp = [left, paper['Id'], paperJId, right]
                        paths.append(pathTmp)

        # 找出形式为 Author -> paper -> conference -> paper 的路径
        if 'C' in right_paper.keys():
            # 找出右边论文的conference
            rightCId = right_paper['C']['CId']
            for paper in left_papers:
                if 'C' in paper.keys():
                    # C.CId
                    paperCId = paper['C']['CId']
                    # 符合条件的路径加入结果集合
                    if paperCId == rightCId:
                        pathTmp = [left, paper['Id'], paperCId, right]
                        paths.append(pathTmp)

        # 找出形式为 Author -> paper -> field -> paper 的路径
        if 'F' in right_paper.keys():
            # 找出右边论文的field
            rightFIds = [field['FId'] for field in right_paper['F']]
            # 遍历left写的所有论文
            for paper in left_papers:
                if 'F' in paper.keys():
                    # 找出左边论文的field
                    paperFIds = [field['FId'] for field in paper['F']]
                    # 求左边论文与右边论文的field的交集
                    interSec = set(rightFIds) & set(paperFIds)
                    # 路径加入paths集合
                    if interSec:
                        for fid in interSec:
                            pathTmp = [left, paper['Id'], fid, right]
                            paths.append(pathTmp)

        if 'AA' in right_paper.keys():
            # 找出右边论文的作者
            AA = right_paper['AA']
            rightAuIds = [Au['AuId'] for Au in AA]

            # 找出形式为 Author -> paper -> Author -> paper 的路径
            # 遍历left写的所有论文
            for paper in left_papers:
                if 'AA' in paper.keys():
                    # 找出左边论文的作者Id
                    paperAuIds = [Au['AuId'] for Au in paper['AA']]
                    # 求左边论文与右边论文的作者的交集
                    interSec = set(rightAuIds) & set(paperAuIds)
                    if interSec:
                        for AuId in interSec:
                            pathTmp = [left, paper['Id'], AuId, right]
                            paths.append(pathTmp)

            # 找出形式为 Author -> Affiliation -> Author -> paper 的路径
            # 找出left属于的机构
            leftAfIdSet = findAfId(left, response_left)
            ##### not done --------->
            # 通过调用API，找出rightAuIds的机构 但这样速度会变慢


        # 找出形式为 Author -> paper -> paper -> paper 的路径

        # 找出引用了right标识符的论文
        entities = response_url3['entities']
        Ids_Quote_Right = [paper['Id'] for paper in entities]
        # 将列表转换为集合
        Ids_Quote_Right = set(Ids_Quote_Right)

        for paper in left_papers:
            # 论文的RId集合
            RIdSet = findRId(paper)
            # 找集合的交集
            interSec = RIdSet & Ids_Quote_Right
            # 符合条件的路径加进paths中
            if interSec:
                for Id in interSec:
                    pathTmp = [left, paper['Id'], Id, right]
                    paths.append(pathTmp)

    # left是paper,right是Author
    if leftIsId and not rightIsId:

        # url for 返回left的信息
        url_left = genURL(expr='Id=%d' % left, attr=ATTR, count=COUNT)
        # url for 返回right写的所有论文信息
        url_right = genURL(expr='Composite(AA.AuId=%d)' % right, attr=ATTR, count=COUNT)

        # 异步API
        urls = [url_left, url_right]
        api = API()
        q = Queue()
        api.multi_get_async(urls, lambda x: q.put_nowait(x))
        result = q.get()
        result_dict = dict(result)
        # 提取出响应
        response_left = convertToDict(result_dict[url_left].getvalue())
        response_right = convertToDict(result_dict[url_right].getvalue())

        # 返回left的所有信息
        leftPaper = response_left['entities'][0]

        # 返回right写的所有论文信息
        right_papers = response_right['entities']
        # right写的论文Id
        rightPaperIds = [paper['Id'] for paper in right_papers]
        # right的机构
        rightAfIds = findAfId(right,response_right)

        # 找出 1-hop 的路径
        # left的作者
        AA = leftPaper['AA']
        leftAuIdSet = [aa['AuId'] for aa in AA]
        if right in leftAuIdSet:
            paths.append([left, right])

        # 找出 2-hop 的路径
        if 'RId' in leftPaper.keys():
            # 求出left的引用
            RIdSet = leftPaper['RId']
            # 求left的引用与right写的论文的交集
            interSec = set(RIdSet) & set(rightPaperIds)
            # 符合条件的路径加入paths
            if interSec:
                for Id in interSec:
                    pathTmp = [left, Id, right]
                    paths.append(pathTmp)

        # 找出 3-hop 的路径
        # paper -> Journal -> paper -> author
        if 'J' in leftPaper.keys():
            leftJId =leftPaper['J']['JId']
            for paper in right_papers:
                if 'J' in paper.keys():
                    JId = paper['J']['JId']
                    if leftJId == JId:
                        paths.append([left, JId, paper['Id'], right])

        # paper -> conference -> paper -> author
        if 'C' in leftPaper.keys():
            leftCId = leftPaper['C']['CId']
            for paper in right_papers:
                if 'C' in paper.keys():
                    CId = paper['C']['CId']
                    if leftCId == CId:
                        paths.append([left, CId, paper['Id'], right])

        # paper -> field -> paper -> author
        if 'F' in leftPaper.keys():
            leftFIds = [field['FId'] for field in leftPaper['F']]
            for paper in right_papers:
                if 'F' in paper.keys():
                    paperFIds = [field['FId'] for field in paper['F']]
                    interSec = set(leftFIds) & set(paperFIds)
                    if interSec:
                        for fid in interSec:
                            paths.append([left, fid, paper['Id'], right])

# not done    paper -> paper -> paper -> author
        if 'RId' in leftPaper.keys():
            pass

        # paper -> author -> paper -> author
        if 'AA' in leftPaper.keys():
            # 找出left的作者
            AA = leftPaper['AA']
            leftAuIds = [Au['AuId'] for Au in AA]
            # 遍历right写的所有论文
            for paper in right_papers:
                if 'AA' in paper.keys():
                    # 找出作者Id
                    paperAuIds = [Au['AuId'] for Au in paper['AA']]
                    interSec = set(leftAuIds) & set(paperAuIds)
                    if interSec:
                        for AuId in interSec:
                            pathTmp = [left, AuId, paper['Id'], right]
                            paths.append(pathTmp)

# not done   paper -> author -> affiliation -> author
            # 找出 right的机构
            rightAfIds = findAfId(right,response_right)

    if leftIsId and rightIsId:
        # url for 返回left的所有信息
        url_left = genURL(expr='Id=%d' % left, attr='Id,AA.AuId,F.FId,J.JId,C.CId,RId',count=COUNT)
        # url for 返回right的所有信息
        url_right = genURL(expr='Id=%d' % right, attr='Id,AA.AuId,F.FId,J.JId,C.CId,RId', count=COUNT)
        # url for 找出引用了right标识符的论文
        exprTmp = expr = 'RId=%d' % right
        url_citeRight = genURL(exprTmp, attr='Id,AA.AuId,F.FId,J.JId,C.CId,RId', count=COUNT)

        urls = [url_left, url_right, url_citeRight]
        api = API()
        q = Queue()
        # 异步API
        api.multi_get_async(urls, lambda x: q.put_nowait(x))
        result = q.get()
        result_dict = dict(result)
        # 提取出响应
        response_left = convertToDict(result_dict[url_left].getvalue())
        response_right = convertToDict(result_dict[url_right].getvalue())
        response_citeRight = convertToDict(result_dict[url_citeRight].getvalue())

        # 返回left的所有信息
        leftPaper = response_left['entities'][0]

        # 返回right的所有信息
        rightPaper = response_right['entities'][0]

        # 返回引用了right的所有论文
        citeRight_papers = response_citeRight['entities']

        # 引用了right的所有论文的Id
        citeRight_Ids = set([paper['Id'] for paper in citeRight_papers])

        #left的引用的Id
        leftRIds = set(leftPaper['RId'])

        # 返回left和right的JId, CId, FId, AuId 的集合
        leftNext = nextNodes_except_RId(leftPaper)
        rightNext = nextNodes_except_RId(rightPaper)

        # 找出 1-hop 路径
        if rightPaper['Id'] in leftRIds:
            paths.append([left,right])

        # 找出 2-hop 路径
        interSec = leftNext & rightNext
        if interSec:
            for node in interSec:
                paths.append([left, node, right])

        # paper -> RId -> paper
        interSec = leftRIds & citeRight_Ids
        if interSec:
            for rid in interSec:
                paths.append([left, rid, right])

        # 找出 3-hop
        # paper -> (JId,CId,FId,AuId) -> paper -> paper
        for paper in citeRight_papers:
            nextTmp = nextNodes_except_RId(paper)
            interSec = nextTmp & leftNext
            if interSec:
                for node in interSec:
                    paths.append([left, node, paper['Id'], right])

    return paths


if __name__ == '__main__':
    # print(isId(2140251882))
    # print(isId(2145115012))
    AuId = 2145115012
    start = time()
    res = searchPath(1984665689, 2112090702)
    print('paths:')
    print(res)
    print("Elapsed time:",time()-start)
