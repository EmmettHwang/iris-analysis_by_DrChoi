import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from datetime import datetime
from .iris_classifier import build_model, AUGMENT_TRANSFORM, TRANSFORM


class IrisDataset(Dataset):
    def __init__(self, samples, transform=None):
        # samples: list of (image_path, label_index)
        self.samples = samples
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label


def train_model(
    samples,           # list of (path, label_index)
    class_names,       # list of class name strings
    session_id,
    model_type="resnet50",
    epochs=10,
    batch_size=16,
    learning_rate=0.001,
    val_split=0.2,
    save_dir="model/saved",
    log_callback=None,
):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    os.makedirs(save_dir, exist_ok=True)

    # train/val split
    import random
    random.shuffle(samples)
    split = int(len(samples) * (1 - val_split))
    train_samples = samples[:split]
    val_samples = samples[split:]

    train_ds = IrisDataset(train_samples, transform=AUGMENT_TRANSFORM)
    val_ds = IrisDataset(val_samples, transform=TRANSFORM)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    num_classes = len(class_names)
    model = build_model(num_classes, model_type, pretrained=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.5)

    history = []
    best_val_acc = 0.0
    best_model_path = os.path.join(save_dir, f"session_{session_id}_best.pth")

    def log(msg):
        if log_callback:
            log_callback(msg)

    log(f"학습 시작 | device={device} | train={len(train_samples)} val={len(val_samples)}")
    log(f"클래스: {class_names}")

    for epoch in range(epochs):
        # --- train ---
        model.train()
        train_loss, train_correct, train_total = 0, 0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            train_total += labels.size(0)
            train_correct += predicted.eq(labels).sum().item()

        # --- validate ---
        model.eval()
        val_loss, val_correct, val_total = 0, 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        scheduler.step()

        t_acc = train_correct / max(train_total, 1)
        v_acc = val_correct / max(val_total, 1)
        t_loss = train_loss / max(train_total, 1)
        v_loss = val_loss / max(val_total, 1)

        entry = {
            "epoch": epoch + 1,
            "train_loss": round(t_loss, 4),
            "train_acc": round(t_acc, 4),
            "val_loss": round(v_loss, 4),
            "val_acc": round(v_acc, 4),
        }
        history.append(entry)
        log(f"Epoch {epoch+1}/{epochs} | train_acc={t_acc:.3f} val_acc={v_acc:.3f}")

        if v_acc >= best_val_acc:
            best_val_acc = v_acc
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "model_type": model_type,
                    "class_names": class_names,
                    "epoch": epoch + 1,
                    "val_acc": v_acc,
                },
                best_model_path,
            )

    log(f"학습 완료 | best_val_acc={best_val_acc:.4f} | 저장경로={best_model_path}")
    return best_model_path, best_val_acc, history
