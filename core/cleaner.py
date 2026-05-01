import pandas as pd

def clean_excel():
    df = pd.read_excel("data/output.xlsx")
    df = df.drop_duplicates()
    df = df.dropna()
    df.to_excel("data/cleaned.xlsx", index=False)
    return {"status": "cleaned"}
