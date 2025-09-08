import streamlit as st
import pandas as pd
import joblib
import plotly.express as px
import networkx as nx
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Load data and models
df_fake = pd.read_csv('data/fake_profiles.csv')
df_env = pd.read_csv('data/environmental_crimes.csv')
df_connections = pd.read_csv('data/connections.csv')
model = joblib.load('models/fake_detector.pkl')
scaler = joblib.load('models/scaler.pkl')

num_cols = ['followers', 'following', 'bio_length', 'posts_per_month', 'account_age_months']

# Function to get profile info, prediction, and risk score
def get_profile_info(username):
    row = df_fake[df_fake['username'] == username]
    if row.empty:
        return None
    features = row[['followers', 'following', 'bio_length', 'posts_per_month', 'account_age_months', 'verified']].copy()
    features[num_cols] = scaler.transform(features[num_cols])
    prediction = model.predict(features)[0]
    risk_score = model.predict_proba(features)[0][1]  # Probability of being fake (0-1)
    return row.iloc[0], prediction, risk_score

# Function to generate PDF report
def generate_pdf_report(profile, prediction, risk_score):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.drawString(100, 750, "Criminal Profiling Report")
    c.drawString(100, 730, f"Username: {profile['username']}")
    c.drawString(100, 710, f"Followers: {profile['followers']}")
    c.drawString(100, 690, f"Following: {profile['following']}")
    c.drawString(100, 670, f"Bio Length: {profile['bio_length']}")
    c.drawString(100, 650, f"Posts per Month: {profile['posts_per_month']}")
    c.drawString(100, 630, f"Account Age (months): {profile['account_age_months']}")
    c.drawString(100, 610, f"Verified: {'Yes' if profile['verified'] else 'No'}")
    c.drawString(100, 590, f"Prediction: {'Fake' if prediction == 1 else 'Real'}")
    c.drawString(100, 570, f"Risk Score: {risk_score:.2f}")
    c.save()
    buffer.seek(0)
    return buffer

# Streamlit Dashboard
st.title("PSCS_586: Criminal Profiling Using OSINT")

tabs = st.tabs(["Profile Search", "View Datasets", "Criminal Network", "Environmental Crimes Map"])

with tabs[0]:
    st.header("Search for a Profile")
    username = st.text_input("Enter Username (e.g., user_123)")
    if username:
        info = get_profile_info(username)
        if info:
            profile, prediction, risk_score = info
            st.write("### Profile Attributes")
            st.write(profile)
            st.write(f"### Prediction: {'Fake' if prediction == 1 else 'Real'}")
            st.write(f"### Risk Score: {risk_score:.2f} (0 = Low Risk, 1 = High Risk)")
            
            # Export options
            csv_data = pd.DataFrame([profile]).to_csv(index=False).encode('utf-8')
            st.download_button("Export to CSV", csv_data, "profile_report.csv", "text/csv")
            
            pdf_data = generate_pdf_report(profile, prediction, risk_score)
            st.download_button("Export to PDF", pdf_data, "profile_report.pdf", "application/pdf")
        else:
            st.error("Username not found.")

with tabs[1]:
    st.header("Sample Datasets")
    st.subheader("Fake Profiles (First 100 rows)")
    st.dataframe(df_fake.head(100))
    st.subheader("Environmental Crimes (First 100 rows)")
    st.dataframe(df_env.head(100))

with tabs[2]:
    st.header("Criminal Network Visualization")
    st.write("Network graph of connections between suspicious (fake) accounts.")
    G = nx.from_pandas_edgelist(df_connections, 'from_username', 'to_username')
    fig, ax = plt.subplots(figsize=(10, 8))
    nx.draw(G, with_labels=True, node_color='red', edge_color='gray', ax=ax)
    st.pyplot(fig)

with tabs[3]:
    st.header("Environmental Crimes Analysis (SDG 13)")
    df_env['date'] = pd.to_datetime(df_env['date'])
    
    # Filters
    selected_crimes = st.multiselect("Select Crime Types", options=df_env['crime_type'].unique(), default=df_env['crime_type'].unique())
    min_date, max_date = df_env['date'].min().date(), df_env['date'].max().date()
    start_date, end_date = st.date_input("Date Range", [min_date, max_date])
    
    filtered_df = df_env[
        (df_env['crime_type'].isin(selected_crimes)) &
        (df_env['date'] >= pd.to_datetime(start_date)) &
        (df_env['date'] <= pd.to_datetime(end_date))
    ]
    
    # Scatter map
    fig_map = px.scatter_mapbox(
        filtered_df, lat="latitude", lon="longitude", color="crime_type",
        hover_name="crime_type", hover_data=["date", "confidence_level", "source"],
        zoom=0, mapbox_style="open-street-map"
    )
    st.plotly_chart(fig_map)
    
    # Hotspots clustering
    if st.button("Detect Hotspots (KMeans Clustering)"):
        if len(filtered_df) > 0:
            coords = filtered_df[['latitude', 'longitude']]
            kmeans = KMeans(n_clusters=min(5, len(coords)), random_state=42)
            filtered_df['cluster'] = kmeans.fit_predict(coords)
            fig_cluster = px.scatter_mapbox(
                filtered_df, lat="latitude", lon="longitude", color="cluster",
                hover_name="crime_type", zoom=0, mapbox_style="open-street-map"
            )
            st.plotly_chart(fig_cluster)
        else:
            st.warning("No data to cluster.")