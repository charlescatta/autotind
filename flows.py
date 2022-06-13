import json
from typing import Any
from mitmproxy import http
from autotind.flow_utils import BaseInterceptor
from loguru import logger
from handlers import WorkTypes
from autotind.processor import Processor

class LocationInterceptor(BaseInterceptor):
    def __init__(self, processor):
        self.processor = processor

    def accepts(self, flow: http.HTTPFlow):
        return "/v2/meta" in flow.request.path_url and flow.request.method == "POST"

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        flow.response.set_content(json.dumps({ "lat": 45.538099, "lon": -73.604520, "force_fetch_resources": True}))

class RecsInterceptor(BaseInterceptor):
    def __init__(self, processor: Processor) -> None:
        super().__init__()
        self.processor = processor

    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/v2/recs" in flow.request.path and flow.request.method == 'GET'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        if not body:
            return
        data = body.get('data', {})
        results = data.get('results', [])
        for result in results:
            result_data = result.get('user')
            if not result_data:
                logger.warning(f"Rec data missing: {result}")
            self.processor.add_work(WorkTypes.add_rec.value, result_data)
                
class LikeInterceptor(BaseInterceptor):
    def __init__(self, processor: Processor) -> None:
        super().__init__()
        self.processor = processor
    
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/like/" in flow.request.path and flow.request.method == 'POST'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        _, id = flow.request.path_components
        self.processor.add_work(WorkTypes.like.value, id)

class DislikeInterceptor(BaseInterceptor):
    def __init__(self, processor: Processor) -> None:
        super().__init__()
        self.processor = processor
    
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/pass/" in flow.request.path and flow.request.method == 'GET'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        _, id = flow.request.path_components
        self.processor.add_work(WorkTypes.dislike.value, id)


class MatchInterceptor(BaseInterceptor):
    def __init__(self, processor: Processor) -> None:
        super().__init__()
        self.processor = processor
    
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/v2/matches" in flow.request.path and flow.request.method == 'GET'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        if not body:
            return
        data = body.get('data', {})
        matches = data.get('matches', [])
        for match in matches:
            match_data = match.get('person')
            if not match_data:
                logger.warning(f"No person data in match: {match}")
                continue
            self.processor.add_work(WorkTypes.add_match.value, match_data)