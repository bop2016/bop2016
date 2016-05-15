import http.client, urllib.request, urllib.parse, urllib.error, base64
from time import time

def normalAPI(id):
    params = urllib.parse.urlencode({
        # Request parameters
        'expr': 'Id=%s'%id,
        'model': 'latest',
        'attributes': 'Id,Ti,AA.AuId,AA.AfId,F.FId,J.JN,J.JId,C.CId,RId',
        'count': '1000000',
        'offset': '0',
        'subscription-key': 'f7cc29509a8443c5b3a5e56b0e38b5a6',
    })

    try:
        conn = http.client.HTTPSConnection('oxfordhk.azure-api.net')
        conn.request("GET", "/academic/v1.0/evaluate?%s" % params)
        response = conn.getresponse()
        data = response.read()
        conn.close()
    except Exception as e:
        print("[Errno {0}] {1}".format(e.errno, e.strerror))
    return data

t1 = time()
data = normalAPI(2112090702)
print(data)
print('Elapsed time of normalAPI:',time()-t1)

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