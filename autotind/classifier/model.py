from typing import Iterable
import torch
import torchvision
import torchmetrics
import pytorch_lightning as pl
from torch.functional import F
from torch import nn
from torchvision import transforms
from autotind.classifier.dataset import PersonDataModule

class SequenceWise(nn.Module):
    """
    Sequence wise application of a module, expects a tensor of shape (n_batch, n_seq, d_1, d_2, ..., d_n))
    
    """
    def __init__(self, module: nn.Module):
        super().__init__()
        self.module = module

    def forward(self, x: torch.Tensor):
        n_batch, n_seq = x.shape[:2]
        data_shape = x.shape[2:]
        x = x.view(-1, *data_shape)
        x = self.module(x)
        x = x.view(n_batch, n_seq, *x.shape[1:])
        return x

    def __repr__(self):
        return f"{self.__class__.__name__} (\n{self.module.__repr__()})"   


class SequenceWiseImageEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()


class PersonClassifier(pl.LightningModule):
    def __init__(self, lr: float = 5e-3, freeze_encoder: bool = False):
        super().__init__()
        embedder = torchvision.models.resnet34(pretrained=True)
        self.train_accuracy = torchmetrics.Accuracy()
        self.valid_accuracy = torchmetrics.Accuracy()
        self.img_encoder = SequenceWise(nn.Sequential(*list(embedder.children())[:-1]))
        if freeze_encoder:
            for param in self.img_encoder.parameters():
                param.requires_grad = False
        else:
            for param in self.img_encoder.parameters():
                param.requires_grad = True
        self.img_embedding_size = embedder.fc.in_features
        self.lr = lr
        self.gru = nn.GRU(self.img_embedding_size, 128, 2, batch_first=True, dropout=0.1)
        self.gru_h0: nn.Parameter = nn.Parameter(torch.randn(2, 128), requires_grad=True).type(torch.FloatTensor)
        self.classifier = nn.Sequential(
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 100),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(100, 50),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(50, 2),
            nn.Softmax()
        )
    
    def forward(self, batch):
        x, lengths, labels = batch
        x = self.img_encoder(x)
        x.squeeze_(-1).squeeze_(-1)

        # Make initial state a learned parameter instead of zeros
        # https://r2rt.com/non-zero-initial-states-for-recurrent-neural-networks.html
        h0 = self.gru_h0.repeat(x.shape[0], 1, 1)
        #TODO use PackedSequence
        x, _ = self.gru(x, h0)
        x = x[:, -1, :] # take last hidden state
        x = self.classifier(x)
        return x

    def loss(self, y_hat, y):
        return F.cross_entropy(y_hat, y)

    def training_step(self, batch, batch_idx):
        imgs, lengths, y = batch
        y_hat = self(batch)

        loss = self.loss(y_hat, y)

        self.log('train_loss', loss, on_step=True, on_epoch=True)
        self.train_accuracy.update(y_hat, y.int())

        return loss
    
    def training_epoch_end(self, outputs: Iterable[dict]) -> None:
        self.log('train_acc', self.train_accuracy.compute())
        self.train_accuracy.reset()


    def validation_step(self, batch, batch_idx):
        imgs, lengths, y = batch
        y_hat = self(batch)
        
        loss = self.loss(y_hat, y)

        self.log('val_loss', loss, on_step=True, on_epoch=True)

        self.valid_accuracy.update(y_hat, y.int())
        
        return loss

    def validation_epoch_end(self, outputs: Iterable[dict]) -> None:
        self.log('val_acc', self.valid_accuracy.compute())
        self.valid_accuracy.reset()

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.lr)

train_tfms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

val_tfms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor()
])


if __name__ == '__main__':
    from pytorch_lightning.loggers import WandbLogger
    dm = PersonDataModule('sqlite:///tind.sqlite', './images', batch_size=2, train_tfms=train_tfms, val_tfms=val_tfms)
    # sample_dm(dm)

    model = PersonClassifier(lr=5e-6, freeze_encoder=False)
    trainer = pl.Trainer(accelerator="gpu", max_epochs=50, enable_progress_bar=True, logger=WandbLogger(project="tind-classifier"), accumulate_grad_batches=5)
    trainer.fit(model, dm)
    # tuner = trainer.tuner.lr_find(model, dm)
    # tuner.plot(suggest=True, show=True)
