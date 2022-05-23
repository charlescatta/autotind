import io
import json
from typing import Any
from mitmproxy import http
from data.db import PType, Person


def save_tinder_recs(flow: http.HTTPFlow, sess: Any) -> None:
    if "/v2/recs" in flow.request.path and flow.request.method == 'GET':
        print("Intercepted recs request: ", flow.request.path)
        data = flow.response.get_content()
        if not data:
            return
        data: dict = json.load(io.BytesIO(data))
        data: dict = data.get('data')
        if data and data.get('results'):
            print("Found {} recs".format(len(data.get('results'))))
            for rec in data.get('results'):
                person = rec.get('person') or rec.get('user')
                if not person:
                    print("Expected person in rec, but got: {}".format(rec))
                person = Person.from_json(person, PType.REC.value)
                if person:
                    sess.merge(person)
                    sess.commit()

def save_tinder_matches(flow: http.HTTPFlow, sess: Any):
    if "/v2/matches" in flow.request.path and flow.request.method == 'GET':
        print("Intercepted matches request: ", flow.request.path)
        data = flow.response.get_content()
        if not data:
            return
        data = json.load(io.BytesIO(data))
        data: dict = data.get('data')
        if data and data.get('matches'):
            print("Found {} matches".format(len(data.get('matches'))))
            for match in data.get('matches'):
                person = Person.from_json(match['person'], PType.MATCH.value)
                if person:
                    person.save(sess)
                

def save_tinder_likes(flow: http.HTTPFlow, sess: Any):
    if "/like/" in flow.request.path and flow.request.method == 'POST':
        print("Intercepted like request: ", flow.request.path)
        _, id = flow.request.path_components
        print("Liked {}".format(id))
        sess.query(Person).filter(Person.id == id).update({'type': PType.LIKE.value})
        sess.commit()

def save_tinder_dislikes(flow: http.HTTPFlow, sess: Any):
    if "/pass/" in flow.request.path and flow.request.method == 'GET':
        print("Intercepted dislike request: ", flow.request.path)
        _, id = flow.request.path_components
        print("Disliked {}".format(id))
        sess.query(Person).filter(Person.id == id).update({'type': PType.DISLIKE.value})
        sess.commit()