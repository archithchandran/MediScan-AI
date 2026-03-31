import pandas as pd
from sklearn.tree import DecisionTreeClassifier

data = {
    'bp': [110,120,130,140,150,160],
    'sugar': [90,110,130,160,180,200],
    'bmi': [22,24,26,28,32,35],
    'heart': [70,75,80,85,90,95],
    'risk': ['Low','Low','Medium','Medium','High','High']
}

df = pd.DataFrame(data)

X = df[['bp','sugar','bmi','heart']]
y = df['risk']

model = DecisionTreeClassifier()
model.fit(X, y)

def predict_risk(bp, sugar, bmi, heart):
    return model.predict([[bp, sugar, bmi, heart]])[0]