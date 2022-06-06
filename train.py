# %%
from sqlalchemy import select
from autotind.db import Person, DB, PType, ImageStatus
import matplotlib.pyplot as plt

db = DB()

session = db.create_session()

# %%
from PIL import Image

def is_image_file_valid(image_file):
    try:
        image = Image.open(image_file)
        image.close()
        return True
    except:
        return False

peoples = session.query(Person).all()

# %%
import pandas as pd

full_dataset = []

def get_type(type):
    if type == PType.MATCH.value:
        return 'like'
    return type

for people in peoples:
    for photo in people.photos:
        if photo.save_path.exists() and is_image_file_valid(photo.save_path):
            full_dataset.append([str(photo.save_path), get_type(people.type)])

df = pd.DataFrame(full_dataset, columns=['image', 'type'])

# %%
from sklearn.model_selection import train_test_split

train_df, test_df = train_test_split(df, test_size=0.2)


# %%
print(len(peoples))

# %%
import flash
from flash.image import ImageClassificationData, ImageClassifier

data = ImageClassificationData.from_data_frame('image', 'type', train_data_frame=train_df, val_data_frame=test_df, batch_size=16)
model = ImageClassifier(backbone="resnet50", labels=data.labels)

trainer = flash.Trainer(max_epochs=20, accelerator="gpu")
trainer.finetune(model, data)
