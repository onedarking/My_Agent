import os
import shutil

def organize_files():
    for f in os.listdir("data"):
        if f.endswith(".pdf"):
            os.makedirs("data/pdf", exist_ok=True)
            shutil.move(f"data/{f}", f"data/pdf/{f}")
    return {"status": "organized"}
