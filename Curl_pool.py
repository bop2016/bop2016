from queue import Queue
import pycurl

class Curl_pool(object):
    ''' a pool to relief the cost of allocating Curl object '''
    def __init__(self):
        self._Curl_objects = Queue()

    def get_obj(self):
        try:
            return self._Curl_objects.get_nowait()
        except Exception:  # the queue is empty
            for i in range(9):
                self._Curl_objects.put_nowait(pycurl.Curl())
            return pycurl.Curl()

    def return_objs(self, Curl_objs):  # should this be asynchronous?
        for Curl_obj in Curl_objs:
            self._Curl_objects.put_nowait(Curl_obj)

    def return_obj(self, Curl_obj):
        self._Curl_objects.put_nowait(Curl_obj)
