from fastapi import FastAPI
from core.processor import process_files
from core.cleaner import clean_excel
from core.organizer import organize_files

app = FastAPI()

@app.post("/api/process")
def process():
    return process_files()

@app.post("/api/clean")
def clean():
    return clean_excel()

@app.post("/api/organize")
def organize():
    return organize_files()
