import pandas as pd
import torch
import pytorch_lightning as pl
import functools
from typing import Union, Optional, Callable, Tuple
from PIL import Image
from pathlib import Path
from autotind.person import Person
from autotind.db import PersonRepo
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

@functools.lru_cache(maxsize=None)
def get_datasets(sqlite_url: str = 'sqlite:///tind.sqlite', split_frac: float = 0.2, sample_size: Optional[float] = None, equalize_classes: bool = False) -> Tuple[pd.DataFrame, pd.DataFrame]:
    repo = PersonRepo(sqlite_url)
    persons = repo.get_all()

    df = pd.DataFrame(persons)
    
    if sample_size is not None:
        df = df.sample(frac=sample_size)

    df['label'] = df['label'].replace('match', 'like')
    df = df[df['label'] != 'recommendation']

    if equalize_classes:
        sample_size = min(len(df[df['label'] == 'like']), len(df[df['label'] == 'dislike']))
        df = df.groupby('label').apply(lambda x: x.sample(sample_size)).reset_index(drop=True)
    
    train_df, test_df = train_test_split(df, test_size=split_frac)
    return train_df, test_df


class PersonDataset(Dataset):
    def __init__(self, df: pd.DataFrame, img_root_dir: Union[Path, str], tfms: Optional[Callable] = None):
        self.df = df
        self.img_root_dir = Path(img_root_dir)
        self.tfms = tfms
    
    def __len__(self):
        return len(self.df)
    

    def _tfm_label(self, label: str) -> int:
        if label == 'like':
            return 1
        elif label == 'dislike':
            return 0
        else:
            raise ValueError(f"Unknown label: {label}")

    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        p = Person.from_dict({**row})
        imgs = []
        for idx, photo in enumerate(p.photos):
            img_path = photo.get_path(self.img_root_dir)
            img = Image.open(img_path)
            img = img.convert('RGB')
            if self.tfms:
                img = self.tfms(img)
            imgs.append(img)
        if len(imgs) < 1:
            raise ValueError(f"No images found for person: {p}")
        return imgs, self._tfm_label(p.label)


class PersonDataModule(pl.LightningDataModule):
    def __init__(self, db_url: str, img_root_dir: Union[Path, str], batch_size: int = 2, train_tfms: Optional[Callable] = None, val_tfms: Optional[Callable] = None):
        super().__init__()
        self.img_root_dir = Path(img_root_dir)
        self.db_url = db_url
        self.batch_size = batch_size
        self.train_tfms = train_tfms
        self.val_tfms = val_tfms

    @staticmethod
    def collate_fn(batch):
        sorted_batch = sorted(batch, key=lambda x: len(x[0]), reverse=True)
        imgs = [torch.stack(d[0]) for d in sorted_batch]
        img_pack = torch.nn.utils.rnn.pad_sequence(imgs, batch_first=True)
        lengths = torch.LongTensor([len(d[0]) for d in sorted_batch])
        labels = torch.LongTensor([d[1] for d in sorted_batch])
        return img_pack, lengths, labels

    def setup(self, stage: Optional[str] = None):
        self.train_df, self.test_df = get_datasets(self.db_url)

    def train_dataloader(self):
        return DataLoader(PersonDataset(self.train_df, self.img_root_dir, tfms=self.train_tfms), batch_size=self.batch_size, shuffle=True, num_workers=4, collate_fn=self.collate_fn)

    def val_dataloader(self):
        return DataLoader(PersonDataset(self.test_df, self.img_root_dir, tfms=self.val_tfms), batch_size=self.batch_size, shuffle=False, num_workers=4, collate_fn=self.collate_fn)