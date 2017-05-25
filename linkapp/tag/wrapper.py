import requests
import time

class TooManyRetries(Exception):
    """
    Raised when a request is retried too many times.
    """
    
class NotFound(Exception):
    """
    Raised when a call to the service returns a 404 status code.
    """

class ServiceWrapper:
    
    def __init__(self, base_url, timeout=2, retries=10, sleep=0.1):
        self.base_url = base_url
        self.max_retries = retries
        self.retries = 1
        self.sleep = sleep
        self.timeout = timeout
        
    def wait(self):
        return self.sleep*(self.retries**2)
        
    def _call(self, func, *args, **kwargs):
        if self.retries >= self.max_retries:
            raise TooManyRetries("Maximum retries of {} exceeded".format(self.retries))
            
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException:
            time.sleep(self.wait())
            self.retries += 1
            return func(*args, **kwargs)
        
    def get(self, path):
        r = self._call(requests.get,
                       "{}{}".format(self.base_url, path),
                       headers={"content-type": "application/json"},
                       timeout=self.timeout)
        
        if r.status_code == 404:
            raise NotFound()
            
        return r.json()

        