import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)

# Generate Fake Profiles Dataset (5,000 rows)
n = 5000
usernames = [f"user_{i}" for i in range(n)]
followers = np.random.randint(0, 10000, n)
following = np.random.randint(0, 1000, n)
bio_length = np.random.randint(0, 200, n)
posts_per_month = np.random.randint(0, 100, n)
account_age_months = np.random.randint(1, 120, n)  # in months
verified = np.random.choice([0, 1], n, p=[0.9, 0.1])

# Synthetic labels: higher chance of fake if low followers + high following, or unverified + low activity
labels = np.where(
    (followers < 100) & (following > 500) | (verified == 0) & (posts_per_month < 5),
    1,  # fake
    np.random.choice([0, 1], n, p=[0.8, 0.2])  # mostly real, with some randomness
)

df_fake = pd.DataFrame({
    'username': usernames,
    'followers': followers,
    'following': following,
    'bio_length': bio_length,
    'posts_per_month': posts_per_month,
    'account_age_months': account_age_months,
    'verified': verified,
    'label': labels
})
df_fake.to_csv('data/fake_profiles.csv', index=False)
print("Generated data/fake_profiles.csv")

# Generate Environmental Crimes Dataset (2,000 rows)
m = 2000
latitudes = np.random.uniform(-90, 90, m)
longitudes = np.random.uniform(-180, 180, m)
start_date = datetime(2020, 1, 1)
dates = [start_date + timedelta(days=random.randint(0, 2000)) for _ in range(m)]
crime_types = np.random.choice(['logging', 'poaching', 'mining', 'pollution'], m)
confidence_levels = np.random.choice(['low', 'medium', 'high'], m)
sources = np.random.choice(['satellite', 'report', 'news'], m)

df_env = pd.DataFrame({
    'latitude': latitudes,
    'longitude': longitudes,
    'date': [d.strftime('%Y-%m-%d') for d in dates],
    'crime_type': crime_types,
    'confidence_level': confidence_levels,
    'source': sources
})
df_env.to_csv('data/environmental_crimes.csv', index=False)
print("Generated data/environmental_crimes.csv")

# Generate Synthetic Connections for Suspicious Accounts (for network visualization)
# Select 100 suspicious users (fake labels) and create 200 random edges
suspicious_users = df_fake[df_fake['label'] == 1]['username'].sample(100).tolist()
edges = []
for _ in range(200):
    from_user = random.choice(suspicious_users)
    to_user = random.choice(suspicious_users)
    if from_user != to_user:
        edges.append((from_user, to_user))

df_connections = pd.DataFrame(edges, columns=['from_username', 'to_username'])
df_connections.to_csv('data/connections.csv', index=False)
print("Generated data/connections.csv")