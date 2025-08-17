import pandas as pd

df = pd.read_csv("sales.csv")  # CSV読込
print("合計売上:", df["amount"].sum())
