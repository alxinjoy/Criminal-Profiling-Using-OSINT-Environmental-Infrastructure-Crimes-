import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
import os

# Create models directory if it doesn't exist
os.makedirs('models', exist_ok=True)

# Load dataset
df = pd.read_csv('data/fake_profiles.csv')

# Data Preprocessing
# No missing values in synthetic data, but handle generally
df = df.dropna()

# Features and target
features = ['followers', 'following', 'bio_length', 'posts_per_month', 'account_age_months', 'verified']
X = df[features]
y = df['label']

# Normalize numerical features
num_cols = ['followers', 'following', 'bio_length', 'posts_per_month', 'account_age_months']
scaler = StandardScaler()
X[num_cols] = scaler.fit_transform(X[num_cols])

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train Random Forest Classifier
model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1 Score: {f1:.4f}")

# Save model and scaler
joblib.dump(model, 'models/fake_detector.pkl')
joblib.dump(scaler, 'models/scaler.pkl')

# Save metadata
with open('models/metadata.txt', 'w') as f:
    f.write(f"Accuracy: {accuracy:.4f}\n")
    f.write(f"Precision: {precision:.4f}\n")
    f.write(f"Recall: {recall:.4f}\n")
    f.write(f"F1 Score: {f1:.4f}\n")
print("Model trained and saved to models/")