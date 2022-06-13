import json
import requests
from PIL import Image
from typing import Any, Dict, List, Union
from pathlib import Path
from loguru import logger
from dateutil import parser
from autotind.person import Label, Person, Photo
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, create_engine

Base = declarative_base()

def is_valid_image(path: Union[str, Path]) -> bool:
    try:
        Image.open(path)
        return True
    except Exception as e:
        return False


class InvalidPhotoURLException(Exception):
    pass

class PhotoDB(Base):
    __tablename__ = 'photo'
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('person._id'), nullable=False)
    url = Column(String)
    fileName = Column(String, nullable=False)
    crop_info = Column(String, nullable=True)
    media_type = Column(String, nullable=False)
    rank = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    win_count = Column(Integer, nullable=True)

    @staticmethod
    def from_photo(photo: Photo) -> 'PhotoDB':
        return PhotoDB(
            id=photo.id,
            user_id=photo.user_id,
            url=photo.url,
            fileName=photo.fileName,
            crop_info=json.dumps(photo.crop_info),
            media_type=photo.media_type,
            score=photo.score,
            win_count=photo.win_count,
            rank=photo.rank
        )

    def to_photo(self) -> "Photo":
        return Photo(
            id=self.id,
            user_id=self.user_id,
            url=self.url,
            fileName=self.fileName,
            crop_info=json.loads(self.crop_info),
            media_type=self.media_type,
            score=self.score,
            win_count=self.win_count,
            rank=self.rank
        )

class PersonDB(Base):
    __tablename__ = 'person'
    _id = Column(String, primary_key=True)
    label = Column(String, nullable=False)
    name = Column(String, nullable=False)
    birth_date = Column(DateTime)
    bio = Column(String, nullable=True)
    gender = Column(Float, nullable=True)
    distance_mi = Column(Float, nullable=True)
    photos = relationship("PhotoDB", backref="person")

    @staticmethod
    def from_person(person: Person) -> "PersonDB":
        photos = [ PhotoDB.from_photo(photo) for photo in person.photos ]
        return PersonDB(
            _id=person._id,
            label=person.label,
            name=person.name,
            birth_date=parser.parse(person.birth_date),
            bio=person.bio,
            gender=person.gender,
            distance_mi=person.distance_mi,
            photos=photos
        )
    
    def to_person(self) -> "Person":
        return Person(
            _id=self._id,
            label=self.label,
            name=self.name,
            birth_date=self.birth_date.isoformat(),
            bio=self.bio,
            gender=self.gender,
            distance_mi=self.distance_mi,
            photos=[p.to_photo() for p in self.photos]
        )

class PersonRepo:
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        Base.metadata.create_all(self.engine)
    
    def upsert(self, person: Person):
        session = self.Session()
        try:
            p = PersonDB.from_person(person)
            self._download_photos(person)
            session.merge(p)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e

    def _download_photos(self, person: Person):
        path = person.get_path('./images')
        path.mkdir(parents=True, exist_ok=True)

        for photo in person.photos:
            path = photo.get_path('./images')
            if path.exists():
                if is_valid_image(path):
                    continue
                else:
                    logger.info(f"Deleting invalid image: {path}")
                    path.unlink()

            try:
                req = requests.get(photo.url, stream=True)
                req.raise_for_status()

                with open(path, 'wb') as f:
                    for chunk in req.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            f.flush()

            except Exception as e:
                path.unlink(missing_ok=True)
                if req.status_code == 403:
                    e = f"403 Forbidden: {photo.url[:50]}"
                raise InvalidPhotoURLException(e)

    def like(self, id: str):
        session = self.Session()
        session.query(PersonDB).where(PersonDB._id == id).update({ "label": Label.LIKE.value })
        session.commit()
    
    def dislike(self, id: str):
        session = self.Session()
        session.query(PersonDB).where(PersonDB._id == id).update({ "label": Label.DISLIKE.value })
        session.commit()

    def get_all(self) -> List[Person]:
        session = self.Session()
        return [ p.to_person() for p in session.query(PersonDB).all() ]

    def where(self, condition: Dict[str, Any]) -> List[Person]:
        session = self.Session()
        return [ p.to_person() for p in session.query(PersonDB).filter_by(**condition).all() ]
