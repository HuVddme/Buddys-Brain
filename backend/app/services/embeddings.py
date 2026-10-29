from functools import lru_cache
import os
from pathlib import Path
import tempfile
from threading import Lock

_model_lock = Lock()


@lru_cache(maxsize=1)
def get_embedding_model():
    # Do not download/load a model during application discovery or import.
    from sentence_transformers import SentenceTransformer
    options = {}
    if os.getenv("VERCEL") == "1":
        options["cache_folder"] = str(Path(tempfile.gettempdir()) / "buddysbrain-models")
    return SentenceTransformer("all-MiniLM-L6-v2", **options)

def get_embedding(text):
    if not text:
        return []
    # lru_cache alone can load twice on simultaneous cold requests.
    with _model_lock:
        model = get_embedding_model()
    return model.encode(text).tolist()
