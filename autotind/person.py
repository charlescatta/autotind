from dataclasses import dataclass, fields, asdict
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union
from loguru import logger


class Label(Enum):
    REC = 'recommendation'
    DISLIKE = 'dislike'
    MATCH = 'match'
    LIKE = 'like'

def pick_dict(d: dict, keys: List[Union[str, Tuple[str, Any]]]) -> dict:
    output = {}
    for key in keys:
        value = d.get(key, None)
        if value != None:
            output[key] = value
    return output

@dataclass(frozen=True)
class Photo:
    id: str
    user_id: str
    url: str
    fileName: str
    crop_info: dict
    media_type: str
    rank: int = -1
    score: float = -1
    win_count: int = -1

    def __repr__(self) -> str:
        return f"<Photo(id={self.id} url='{self.url[:40]}' fileName={self.fileName})>"
    
    def to_dict(self) -> dict:
        return asdict(self)

    def get_path(self, root_dir: Union[str, Path]) -> Path:
        return Path(root_dir) / Path(self.user_id) / Path(self.fileName)

    @staticmethod
    def from_dict(photo_data: dict) -> Optional['Photo']:
        data = {}
        for field in fields(Photo):
            value = photo_data.get(field.name, None)
            if value != None:
                data[field.name] = value
        try:
            return Photo(**data)
        except Exception as e:
            logger.warning(f"Error creating photo: {e}")
            return None

@dataclass(frozen=True)
class Person:
    _id: str
    label: Label
    name: str
    birth_date: date
    photos: List[Photo]
    bio: str = None
    gender: int = None
    distance_mi: int = -1

    def __repr__(self) -> str:
        return f"<Person(id={self._id}, name={self.name}, birthday={self.birth_date} photos={len(self.photos)}) type={self.label}>"

    def to_dict(self) -> dict:
        return asdict(self)
    
    def get_path(self, root_dir: Union[str, Path]) -> Path:
        return Path(root_dir) / Path(self._id)

    @staticmethod
    def from_dict(person_data: dict) -> Optional['Person']:
        data = {}
        user_id = person_data.get('_id', None)

        if not user_id:
            return None

        for field in fields(Person):
            value = person_data.get(field.name, None)
            if field.name == 'photos':
                value = [ Photo.from_dict({**photo, 'user_id': user_id }) for photo in person_data.get('photos', []) ]
                value = [ photo for photo in value if photo ]
            if value != None:
                data[field.name] = value
        try:
            return Person(**data)
        except Exception as e:
            logger.warning(f"Error creating person: {e}")
            return None


