import pytorch_lightning as pl
import matplotlib.pyplot as plt

def sample_dm(dm: pl.LightningDataModule):
    dm.setup()
    imgs, _, ys = next(iter(dm.train_dataloader()))
    for profile in imgs:
        plt.figure(figsize=(10, 10))
        for idx, img in enumerate(profile):
            plt.subplot(1, len(profile)+1, idx+1)
            plt.imshow(img.permute(1, 2, 0))
        plt.show()