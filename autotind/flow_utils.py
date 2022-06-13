from abc import ABC, abstractmethod
import io
import json
from mitmproxy import http
from typing import Any, List, Optional

def read_json_body(flow: http.HTTPFlow) -> Optional[dict]:
    try:
        data = flow.response.get_content()
        if not data:
            return None
        json_dict = json.load(io.BytesIO(data))
        return json_dict
    except:
        return None

class BaseInterceptor(ABC):
    type = 'response'
    @abstractmethod
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return NotImplemented
    
    @abstractmethod
    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        return NotImplemented

    def __call__(self, flow: http.HTTPFlow):
        if not self.accepts(flow):
            return
        if self.type == 'request':
            self.process(flow, None)
        elif self.type == 'response':
            body = read_json_body(flow)
            self.process(flow, body)

class InterceptorMiddleware:
    def __init__(self, interceptors: List[BaseInterceptor]):
        self.interceptors = interceptors

    def request(self, flow: http.HTTPFlow):
        interceptors = [i for i in self.interceptors if i.type == 'request']
        for interceptor in interceptors:
            interceptor(flow)
    
    def response(self, flow: http.HTTPFlow):
        interceptors = [i for i in self.interceptors if i.type == 'response']
        for interceptor in interceptors:
            interceptor(flow)