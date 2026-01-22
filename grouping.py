import torch
import numpy as np
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
import os
from sklearn.cluster import KMeans
from collections import defaultdict
import numpy as np
import shutil



MODEL_ID = "facebook/dinov2-base"  # small/base/large models also exist on HF
device = "mps" if torch.backends.mps.is_available() else "cpu"

processor = AutoImageProcessor.from_pretrained(MODEL_ID)
model = AutoModel.from_pretrained(MODEL_ID).to(device)
model.eval()

@torch.no_grad()
def embed_image(path: str) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    inputs = processor(images=img, return_tensors="pt").to(device)

    outputs = model(**inputs)
    # last_hidden_state: [batch, tokens, dim]
    feats = outputs.last_hidden_state

    cls = feats[:, 0]  # [batch, dim] - global embedding (CLS token) :contentReference[oaicite:6]{index=6}
    cls = torch.nn.functional.normalize(cls, dim=-1)  # good for cosine similarity
    return cls[0].cpu().numpy()

def list_images(folder: str):
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f.lower())[1] in exts
    ]

# 1) build embeddings
paths = list_images("/Users/copeland/Pictures/Film/Jade Color '25/Media Res")
embs = np.stack([embed_image(p) for p in paths]).astype("float32")
# embs are already L2-normalized, so inner product == cosine similarity



k = 15
kmeans = KMeans(n_clusters=k, random_state=0, n_init="auto")
labels = kmeans.fit_predict(embs)

clusters = defaultdict(list)
for p, lab in zip(paths, labels):
    clusters[int(lab)].append(p)

if os.path.exists("clusters"):
    shutil.rmtree("clusters")
os.makedirs("clusters")


for lab in range(k):
    os.makedirs(f"clusters/{lab}")
    print(f"\nCluster {lab} ({len(clusters[lab])} images)")
    for p in clusters[lab]:
        print(f"  {p}")
        shutil.copy(p, f"clusters/{lab}/")