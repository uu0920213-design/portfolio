import pandas as pd

df = pd.read_csv("data/intent_train.csv")

print(df.head())
print(df["intent"].value_counts())