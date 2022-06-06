import json
from typing import Optional
from sqlalchemy import String, Column, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, sessionmaker, Session, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum
from pathlib import Path
from dateutil import parser
from .config import config

class PType(Enum):
    REC = 'recommendation'
    DISLIKE = 'dislike'
    MATCH = 'match'
    LIKE = 'like'


class ImageStatus(Enum):
    NOTDOWNLOADED = 'not-downloaded'
    DOWNLOADING = 'downloading'
    DOWNLOADED = 'downloaded'
    ERROR = 'error'

Base = declarative_base()

class DB:
    def __init__(self):
        self.engine = create_engine(config.DB_URL)
        Base.metadata.create_all(self.engine)
        sess_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(sess_factory)
    
    def create_session(self) -> Session:
        return self.Session()

class Photo(Base):
    __tablename__ = 'photo'
    id = Column(String, primary_key=True)
    person_id = Column(String, ForeignKey('person.id'), nullable=False)
    url = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    crop_info = Column(String, nullable=True)
    status = Column(String, nullable=False, default=ImageStatus.NOTDOWNLOADED.value)

    def __init__(self, id: str, person_id: str, url: str, filename: str, crop_info: str, status: ImageStatus):
        self.id = id
        self.person_id = person_id
        self.url = url
        self.filename = filename
        self.crop_info = crop_info
        self.status = status
    
    @property
    def save_path(self):
        return Path(config.IMG_SAVE_PATH) / self.person_id / self.filename

    def __repr__(self) -> str:
        return f"<Photo(id='{self.id}', person_id='{self.person_id}', filename='{self.filename}', status='{self.status}')>"
    @staticmethod
    def from_json(person_id: str, photo_data: dict) -> Optional['Photo']:
        if 'crop_info' in photo_data:
            crop_info = json.dumps(photo_data['crop_info'])
        else:
            crop_info = None
        return Photo(
            id=photo_data.get('id'),
            person_id=person_id,
            url=photo_data.get('url'),
            filename=photo_data.get('fileName'),
            crop_info=crop_info,
            status=ImageStatus.NOTDOWNLOADED.value
        )

class Person(Base):
    __tablename__ = 'person'
    id = Column(String, primary_key=True)
    type = Column(String, nullable=False, default=PType.REC)
    name = Column(String)
    birthday = Column(DateTime)
    photos = relationship("Photo", backref="person")

    def __repr__(self) -> str:
        return f"<Person(id={self.id}, name={self.name}, birthday={self.birthday} photos={len(self.photos)}) type={self.type}>"
    
    @staticmethod
    def from_json(user: dict, type: PType = PType.REC) -> Optional['Person']:
        user_id = user.get('_id')
        if user_id is None:
            return None
        photos = [ Photo.from_json(user_id, photo) for photo in user.get('photos', []) ]
        photos = [ p for p in photos if p is not None ]
        birthday = parser.parse(user.get('birth_date')) if user.get('birth_date') else None
        return Person(
            id=user_id,
            name=user.get('name'),
            birthday=birthday,
            type=type,
            photos=photos
        )

    def save(self, session: Session):
        for photo in self.photos:
            session.merge(photo)
        session.merge(self)
        session.commit()

