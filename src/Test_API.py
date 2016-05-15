import pycurl, urllib.parse
from time import time
from queue import Queue
from API import API
import grequests

if __name__ == '__main__':
    params = urllib.parse.urlencode({
        # Request parameters
        'expr': 'Composite(AA.AuN==\'jaime teevan\')',
        'model': 'latest',
        'attributes': 'Ti,Y,CC,AA.AuN,AA.AuId',
        'count': '2',
        'offset': '0',
        'subscription-key': 'f7cc29509a8443c5b3a5e56b0e38b5a6',
    })

    urls = ['http://oxfordhk.azure-api.net/academic/v1.0/evaluate?%s' % params] * 100
    q = Queue()
    api = API()
    # run 3 times to observe the effect of Curl_pool and obtain average time
    for i in range(10):
        start_time = time()
        api.multi_get_async(urls, lambda x: q.put_nowait(x))
        result = q.get()
        print(result[0][1].getvalue()[:10])
        print('Elapsed time of multi_get: %f' % (time() - start_time))
        start_time = time()
        api.multi_get_grequests(urls)
        print('Elapsed time of grequests: %f' % (time() - start_time))

    print(api.get('http://oxfordhk.azure-api.net/academic/v1.0/evaluate?%s' % params).getvalue()[:10])
