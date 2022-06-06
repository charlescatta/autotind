import json
from typing import Any, Optional
from mitmproxy import http
from autotind.db import DB, PType, Person
from autotind.flow_utils import BaseInterceptor
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.NOTSET)

class RecsInterceptor(BaseInterceptor):
    def __init__(self, db: DB, logger: logging.Logger = logger) -> None:
        super().__init__()
        self.db = db
        self.logger = logger

    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/v2/recs" in flow.request.path and flow.request.method == 'GET'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        data: Optional[dict] = body.get('data', {})
        recs: list[dict] = data.get('results', [])
        recs = [ rec.get('user', {}) for rec in recs ]
        session = self.db.create_session()
        for person_data in recs:
            exists = session.query(Person).filter(Person.id == person_data['_id']).count()
            if exists:
                continue
            person = Person.from_json(person_data, PType.REC.value)
            if person:
                print(f"Intercepted Rec: {person}")
                person.save(session)
            else:
                print(f"Unable to save rec: {person_data.get('id')}")
                
class LikeInterceptor(BaseInterceptor):
    def __init__(self, db: DB, logger: logging.Logger = logger) -> None:
        super().__init__()
        self.db = db
        self.logger = logger
    
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/like/" in flow.request.path and flow.request.method == 'POST'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        _, id = flow.request.path_components
        session = self.db.create_session()
        session.query(Person).filter(Person.id == id).update({'type': PType.LIKE.value})
        print(f"Liking person with id {id}")
        session.commit()


class DislikeInterceptor(BaseInterceptor):
    def __init__(self, db: DB, logger: logging.Logger = logger) -> None:
        super().__init__()
        self.db = db
        self.logger = logger
    
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/pass/" in flow.request.path and flow.request.method == 'GET'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        _, id = flow.request.path_components
        session = self.db.create_session()
        session.query(Person).filter(Person.id == id).update({'type': PType.DISLIKE.value})
        print(f"Disliking person with id: {id}")
        session.commit()


class MatchInterceptor(BaseInterceptor):
    def __init__(self, db: DB, logger: logging.Logger = logger) -> None:
        super().__init__()
        self.db = db
        self.logger = logger
    
    def accepts(self, flow: http.HTTPFlow) -> bool:
        return "/v2/matches" in flow.request.path and flow.request.method == 'GET'

    def process(self, flow: http.HTTPFlow, body: Any) -> None:
        if not body:
            return
        data: Optional[dict] = body.get('data', {})
        matches: list[dict] = data.get('matches', [])

        session = self.db.create_session()
        for match in matches:
            exists = session.query(Person).filter(Person.id == match.get('id', '')).count()
            if exists:
                continue
            person = Person.from_json(match['person'], PType.MATCH.value)
            print(person)
            if person:
                print(f"Intercepted Match: {person}")
                person.save(session)
            else:
                print(f"Could not create person from match with id: {match.get('id', 'unknown')}")