import os
import pandas as pd
import re

def process_files():
    results = []
    for file in os.listdir("data"):
        if file.endswith(".txt") or file.endswith(".pdf"):
            text = open(f"data/{file}", "r", encoding="utf-8", errors="ignore").read()

            amount = re.findall(r'\d{3,}', text)
            date = re.findall(r'\d{4}-\d{2}-\d{2}', text)

            results.append({
                "file": file,
                "amount": amount[0] if amount else "",
                "date": date[0] if date else ""
            })

    df = pd.DataFrame(results)
    df.to_excel("data/output.xlsx", index=False)

    return results
