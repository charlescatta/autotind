from abc import ABC, abstractmethod
import io
import json
from mitmproxy import http
from typing import Any, List, Optional
from mitmproxy.script import concurrent

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
    @abstractmethod
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return NotImplemented
    
    @abstractmethod
    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        return NotImplemented

    def __call__(self, flow: http.HTTPFlow):
        if self.accepts(flow):
            body = read_json_body(flow)
            self.process(flow, body)

class InterceptorMiddleware:
    def __init__(self, interceptors: List[BaseInterceptor]):
        self.interceptors = interceptors

    
    def response(self, flow: http.HTTPFlow):
        for interceptor in self.interceptors:
            interceptor(flow)