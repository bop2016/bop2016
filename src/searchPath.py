# coding: UTF-8
import time

__author__ = 'Benson'

import http.client
import urllib.request
import urllib.parse
import urllib.error


# 判断标识符是Id还是AuId
# 输入：标识符
# 输出：如果是Id,返回True,如果是AuId，返回False
def isId(id):
    expr = 'Id=%s' % id
    data = callAPI(expr, 10, 'Id,Ti')
    entities = data['entities']
    for entity in entities:
        if 'Ti' in entity.keys():
            return True
    return False


# API的count参数和attr参数
COUNT = 1000000
ATTR = 'Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId'


# 调用API
def callAPI(expr, count=10, attr='Id,Ti,AA.AuId'):
    # expr为查询表达式
    # count为返回结果的数目
    params = urllib.parse.urlencode({
        # Request parameters
        'expr': '%s' % expr,
        'model': 'latest',
        'attributes': '%s' % attr,
        'count': '%d' % count,
        'offset': '0',
        'subscription-key': 'f7cc29509a8443c5b3a5e56b0e38b5a6',
    })

    try:
        conn = http.client.HTTPSConnection('oxfordhk.azure-api.net')
        conn.request("GET", "/academic/v1.0/evaluate?%s" % params)
        response = conn.getresponse()
        data = response.read()
        data = eval(data)
        conn.close()
        return data
    except Exception as e:
        print(e)


# 通过AuId写的论文找出AuId的机构
def findAfId(AuId, paperInfo):
    entities = paperInfo['entities']
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


# 找路径的主函数 未写完 需要补充和优化
def searchPath(left, right):
    # left为左边的标识符, 类型为int64
    # right为右边的标识符, 类型为int64
    if (isId(left)):
        leftIsId = True  # 左边的标识符是Id
    else:
        leftIsId = False  # 左边的标识符是AuId

    if (isId(right)):
        rightIsId = True
    else:
        rightIsId = False

    # 需要返回的路径集合
    res = []

    # 如果左右都是AuId
    if ((not leftIsId) and (not rightIsId)):

        # 返回左边的作者写的所有论文的信息
        expr = 'Composite(AA.AuId=%d)' % left
        leftData = callAPI(expr, count=100000, attr='Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId')

        # 返回右边的作者写的所有论文的信息
        expr = 'Composite(AA.AuId=%d)' % right
        rightPaper = callAPI(expr, count=100000, attr='Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId')

        # 找出左边作者的机构
        leftAfIdSet = findAfId(left, leftData)

        # 找出右边作者的机构
        rightAfIdSet = findAfId(right, rightPaper)

        # 此时1-hop的情况不存在

        #  找出 2-hop 路径
        # 找出left与right共同写的论文
        expr = 'And(Composite(AA.AuId=%d),Composite(AA.AuId=%d))' % (left, right)
        paperInfo = callAPI(expr, 100000)

        # 将中间点是论文的路径加入结果集合中
        entities = paperInfo['entities']
        for entity in entities:
            pathTmp = [int(left), entity['Id'], right]
            res.append(pathTmp)
        print(res)

        # 找出left与right共同的机构
        expr = 'And(Composite(AA.AuId=%d),Composite(AA.AuId=%d))' % (left, right)
        intersec_Af = leftAfIdSet & rightAfIdSet

        # 将中间点是机构的路径加入结果集合
        for af in intersec_Af:
            pathTmp = [left, af, right]
            res.append(pathTmp)

        print(res)

        #  找出 3-hop 路径

        # 求出右边作者写的所有论文的集合
        rightPaperSet = set()
        entities = rightPaper['entities']
        for entity in entities:
            if 'Id' in entity.keys():
                rightPaperSet.add(entity['Id'])

        # 检查左边作者的论文的引用是否在rightPaperSet中，如果在，则将路径加入结果集合
        entities = leftData['entities']
        for entity in entities:
            if 'RId' in entity.keys():
                for rid in entity['RId']:
                    if rid in rightPaperSet:
                        pathTmp = [left, entity['Id'], rid, right]
                        res.append(pathTmp)

    # 如果左边是AuId，右边是Id
    if (not leftIsId) and rightIsId:

        # 返回左边的作者写的所有论文的信息
        expr = 'Composite(AA.AuId=%d)' % left
        leftData = callAPI(expr, count=100000, attr='Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId')
        left_papers = leftData['entities']  # 左边作者写的所有论文

        # 返回右边的论文的所有信息
        expr = 'Id=%d' % right
        rightData = callAPI(expr, count=10000, attr='Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId,RId')
        rightPaper = rightData['entities'][0]


        # 找出 1-hop 路径
        for entity in left_papers:
            if 'Id' in entity.keys():
                if entity['Id'] == right:
                    res.append([left, right])
                    break

        # 找出 2-hop 路径
        for entity in left_papers:
            RId = entity['RId']
            for rid in RId:
                if right == rid:
                    pathTmp = [left, entity['Id'], right]
                    res.append(pathTmp)
                    break

        # 找出 3-hop 路径

        # 找出形式为 Author -> paper -> journal -> paper 的路径
        if 'J' in rightPaper.keys():
            # 找出右边论文的journal
            rightJId = rightPaper['J']['JId']
            # 遍历左边作者的所有论文
            for paper in left_papers:
                if 'J' in paper.keys():
                    paperJId = paper['J']['Id']
                    # 符合条件，路径加入结果集合
                    if paperJId == rightJId:
                        pathTmp = [left, paper['Id'], paperJId, right]
                        res.append(pathTmp)

        # 找出形式为 Author -> paper -> conference -> paper 的路径
        if 'C' in rightPaper.keys():
            # 找出右边论文的conference
            rightCId = rightPaper['C']['CId']
            for paper in left_papers:
                if 'C' in paper.keys():
                    # C.CId
                    paperCId = paper['C']['CId']
                    # 符合条件的路径加入结果集合
                    if paperCId == rightCId:
                        pathTmp = [left, paper['Id'], paperCId, right]
                        res.append(pathTmp)

        # 找出形式为 Author -> paper -> field -> paper 的路径
        if 'F' in rightPaper.keys():
            # 找出右边论文的field
            rightFIds = [field['FId'] for field in rightPaper['F']]
            # 遍历左边的论文
            for paper in left_papers:
                if 'F' in paper.keys():
                    # 找出左边论文的field
                    paperFIds = [field['FId'] for field in paper['F']]
                    # 求左边论文与右边论文的field的交集
                    interSec = set(rightFIds) & set(paperFIds)
                    # 路径加入res集合
                    if interSec:
                        for fid in interSec:
                            pathTmp = [left, paper['Id'], fid, right]
                            res.append(pathTmp)

        if 'AA' in rightPaper.keys():
            # 找出右边论文的作者
            AA = rightPaper['AA']
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
                            res.append(pathTmp)

            # 找出形式为 Author -> Affiliation -> Author -> paper 的路径
            # 找出left属于的机构
            leftAfIdSet = findAfId(left, leftData)
            ##### not done ---——————————————————————————————————>
            # 通过调用API，找出rightAuIds的机构 但这样速度会变慢


        # 找出形式为 Author -> paper -> paper -> paper 的路径

        # 找出引用了right标识符的论文
        expr = 'RId=%d' % right
        referData = callAPI(expr, count=COUNT, attr='Id')
        entities = referData['entities']
        IdsQuoteRight = [paper['Id'] for paper in entities]
        # 将列表转换为集合
        IdsQuoteRight = set(IdsQuoteRight)

        for paper in left_papers:
            # 论文的RId集合
            RIdSet = findRId(paper)
            # 找集合的交集
            interSec = RIdSet & IdsQuoteRight
            # 符合条件的路径加进res中
            if interSec:
                for Id in interSec:
                    pathTmp = [left, paper['Id'], Id, right]
                    res.append(pathTmp)

    # left是paper,right是Author
    if leftIsId and not rightIsId:
        # 返回left的所有信息
        expr = 'Id=%d' % left
        leftData = callAPI(expr, COUNT, attr=ATTR)
        leftPaper = leftData['entities'][0]

        # 返回right写的所有论文信息
        expr = 'Composite(AA.AuId=%d)' % right
        rightData = callAPI(expr, COUNT, attr='Id,AA.AuId,AA.AfId,F.FId,J.JId,C.CId')
        rightEntities = rightData['entities']
        rightPaperSet = [paper['Id'] for paper in rightEntities]

        # 找出 1-hop 的路径
        #left的作者
        AA = leftPaper['AA']
        leftAuIdSet = [aa['AuId'] for aa in AA]
        if right in leftAuIdSet:
            res.append([left,right])

        # 找出 2-hop 的路径
        #求出left的引用
        RIdSet = leftPaper['RId']
        # 求left的引用与right写的论文的交集
        interSec = set(RIdSet) & set(rightPaperSet)
        # 符合条件的路径加入res
        if interSec:
            for Id in interSec:
                pathTmp = [left, Id, right]
                res.append(pathTmp)

        # 找出 3-hop 的路径





    return res


if __name__ == '__main__':
    # print(isId(2140251882))
    # print(isId(2145115012))
    AuId = 2145115012
    res = searchPath(2148606196, 2128308681)
    print('res:')
    print(res)


