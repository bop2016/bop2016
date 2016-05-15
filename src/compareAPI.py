import http.client, urllib.request, urllib.parse, urllib.error, base64
from time import time
import json

#官方的API
def callAPI(expr, attr='Id,Ti,AA.AuId',count=1000000):
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
        data = json.loads(data.decode('UTF-8'))
        conn.close()
        return data
    except Exception as e:
        print(e)

t1 = time()
data = callAPI('Id=2112090702',attr='Id,Ti,AA.AuId,AA.AfId,F.FId,J.JN,J.JId,C.CId,RId',count = 1000000)
t2 = time()
print(data)
print('Elapsed time of official API:',t2-t1)

#国伟的API
from API import API
from searchPath import genURL
api = API()
url = genURL(expr='Id=2112090702' , attr='Id,Ti,AA.AuId,AA.AfId,F.FId,J.JN,J.JId,C.CId,RId',count=1000000)
t1 = time()
data = api.get(url).getvalue().decode('UTF-8')
t2 = time()
print(data)
print('Elapsed time of guowei\' API:',t2-t1)