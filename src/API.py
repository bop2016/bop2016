from Curl_pool import Curl_pool
from threading import Thread
import pycurl
from io import BytesIO
import grequests

class API(object):
    def __init__(self):
        self.curl_pool = Curl_pool()

    def multi_get(self, urls):
        m = pycurl.CurlMulti()
        m.setopt(pycurl.M_PIPELINING, 0)
        # [(url, response)]
        requests = []
        # to keep a python reference count for each handle
        handles = []
        for url in urls:
            response = BytesIO()
            handle = self.curl_pool.get_obj()
            handle.setopt(pycurl.URL, url)
            handle.setopt(pycurl.WRITEFUNCTION, response.write)
            m.add_handle(handle)
            requests.append((url, response))
            handles.append(handle)

        # Perform multi-request
        SELECT_TIMEOUT = 1.0
        # number of remaining active handles
        num_handles = len(requests)
        while num_handles:
            status = m.select(SELECT_TIMEOUT)
            if status == -1:
                continue
            while 1:
                status, num_handles = m.perform()
                if status != pycurl.E_CALL_MULTI_PERFORM: 
                    break
        for handle in handles:
            m.remove_handle(handle)
        self.curl_pool.return_objs(handles)
        return requests

    def multi_get_grequests(self, urls):
        succeeded = []
        retry_count = 0
        while len(urls) and retry_count < 3:
            failed_urls = []
            for url, response in zip(urls, grequests.map((grequests.get(u) for u in urls), gtimeout=5)):
                if response is None:
                    failed_urls.append(url)
                else:
                    succeeded.append((url, BytesIO(response.text.encode('utf-8'))))
            if len(failed_urls) != len(urls):
                urls = failed_urls
                retry_count = 0
            else:
                retry_count += 1
        return succeeded

    def _multi_get_async(self, urls, callback):
        callback(self.multi_get(urls))

    def multi_get_async(self, urls, callback):
        ''' waits until all urls have been got successfully, and then
            calls callback on a list of tuples (url : str, response : BytesIO),
            note that the more urls to get, the more likely to get time out '''
        Thread(target=self._multi_get_async, args=(urls, callback)).start()

    def get(self, url):
        ''' returns a BytesIO object containing the response '''
        handle = self.curl_pool.get_obj()
        response = BytesIO()
        handle.setopt(pycurl.URL, url)
        handle.setopt(pycurl.WRITEDATA, response)
        handle.perform()
        self.curl_pool.return_obj(handle)
        return response
