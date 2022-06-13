from enum import Enum
from loguru import logger
from autotind.person import Label, Person
from autotind.processor import Processor
from autotind.db import PersonRepo


class WorkTypes(Enum):
    add_rec = 'add_rec'
    like = 'like'
    dislike = 'dislike'
    add_match = 'add_match'

def register_work_handlers(processor: Processor):
    personRepo = PersonRepo('sqlite:///tind.sqlite')

    @processor.handler(WorkTypes.add_rec.value)
    def handle_recs(data: dict):
        try:
            person = Person.from_dict(data, Label.REC.value)
            if person:
                logger.info(f"Intercepted Rec: {person.name}")
                personRepo.upsert(person)
            else:
                logger.warning(f"Ignored rec: {data.get('_id')}")
        except Exception as e:
            logger.error(e)


    @processor.handler(WorkTypes.add_match.value)
    def handle_matches(data: dict):
        person = Person.from_dict(data, Label.MATCH.value)
        if person:
            logger.info(f"Intercepted match: {person.name}")
            personRepo.upsert(person)
        else:
            logger.warning(f"Ignored match: {data.get('_id')}")

    @processor.handler(WorkTypes.like.value)
    def add_like(id: str):
        logger.info(f"Liked: {id}")
        personRepo.like(id)

    @processor.handler(WorkTypes.dislike.value)
    def add_dislike(id: str):
        logger.info(f"Dislike: {id}")
        personRepo.dislike(id)
