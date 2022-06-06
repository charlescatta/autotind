from time import sleep
import requests
from PIL import Image
from autotind.db import DB, ImageStatus, Photo


def is_image_file_valid(image_file):
    try:
        image = Image.open(image_file)
        image.close()
        return True
    except:
        return False

def download_photo(photo: Photo):
    photo.save_path.parent.mkdir(parents=True, exist_ok=True)
    
    if photo.save_path.exists() and is_image_file_valid(photo.save_path):
        photo.status = ImageStatus.DOWNLOADED.value
        return photo
    
    with open(photo.save_path, 'wb') as f:
        try:
            response = requests.get(photo.url, stream=True, headers={ "Referer": "https://tinder.com" })
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    return
                f.write(chunk)
            f.flush()
            photo.status = ImageStatus.DOWNLOADED.value
        except Exception as e:
            photo.status = ImageStatus.ERROR.value
            photo.save_path.unlink(missing_ok=True)
            print(f'ERROR downloading image: {e}')
    return photo

def download_images():
    db = DB()
    session = db.create_session()
    try:
        session.query(Photo).filter(Photo.status == ImageStatus.DOWNLOADING.value).update({ Photo.status: ImageStatus.NOTDOWNLOADED.value })
        
        while True:
            photos = session.query(Photo).filter(Photo.status == ImageStatus.NOTDOWNLOADED.value).limit(20).all()
            for photo in photos:
                photo.status = ImageStatus.DOWNLOADING.value
                session.commit()
                
                photo = download_photo(photo)
                
                session.merge(photo)
                session.commit()
                print(f"Downloaded {photo}")
            if not len(photos):  
                sleep(2)

    except KeyboardInterrupt:
        return
   



