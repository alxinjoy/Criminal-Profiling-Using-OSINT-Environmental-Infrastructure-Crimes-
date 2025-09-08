🐍 Step 1: Install Python

Go to the official Python site:
👉 Download Python 3.12 for Windows

Important: During installation, check the box that says:
✅ "Add Python to PATH"
Then click Install Now.

🐍 Step 2: Verify Installation

After installation, open Command Prompt (CMD) again and type:

python --version
pip --version


✅ You should see something like:

Python 3.12.x
pip 24.x


## 📂 Project Structure

```plaintext
📦 PSCS_586
 ┣ 📂 data
 ┃ ┣ 📄 fake_profiles.csv
 ┃ ┣ 📄 environmental_crimes.csv
 ┃ ┗ 📄 connections.csv
 ┣ 📂 models
 ┃ ┣ 📄 fake_detector.pkl
 ┃ ┣ 📄 scaler.pkl
 ┃ ┗ 📄 metadata.txt
 ┣ 📜 generate_datasets.py
 ┣ 📜 train_model.py
 ┣ 📜 app.py
 ┣ 📜 requirements.txt
 ┗ 📜 README.md


🐍 Step 3: Create Project Folder

Inside CMD:

mkdir PSCS_586
cd PSCS_586

🐍 Step 4: Set Up Virtual Environment (Optional but Recommended)
python -m venv venv
venv\Scripts\activate


Now your prompt should show (venv) at the start.

🐍 Step 5: Install Dependencies

Once you create the files (app.py, train_model.py, etc.), also create requirements.txt.
Then install everything:







README.md
text# PSCS_586 — Criminal Profiling Using OSINT (Open Source Intelligence Tools)

## Project Overview
This project builds a system for criminal profiling using OSINT data. It detects fake social media profiles, assigns risk scores, visualizes criminal networks, and analyzes environmental crimes (SDG 13) with maps and hotspots. The system uses synthetic datasets but is designed to be extensible with real OSINT data.

## Folder Structure
- `data/`: Contains CSV datasets (generated).
- `models/`: Trained model files and metadata.
- `generate_datasets.py`: Script to generate synthetic datasets.
- `train_model.py`: Script to train and evaluate the fake profile detection model.
- `app.py`: Streamlit dashboard for interactive visualization and profiling.
- `requirements.txt`: Python dependencies.
- `README.md`: This file.

## Setup and Usage
1. Install dependencies:
pip install -r requirements.txt

text2. Generate datasets:

python generate_datasets.py

textThis creates `fake_profiles.csv`, `environmental_crimes.csv`, and `connections.csv` in `data/`.

3. Train the model:

python train_model.py

textThis trains a Random Forest classifier, evaluates it, and saves files to `models/`.

5. Run the dashboard:
   
streamlit run app.py

textOpen the provided URL in your browser to interact with the dashboard.

## Retraining the Model
- To retrain with new data, replace files in `data/` (ensuring the same schema) and run `python train_model.py`.
- The model uses Random Forest; you can modify `train_model.py` to use Logistic Regression or SVM.

## Extending with Real Data
- Replace synthetic CSVs in `data/` with real datasets from Kaggle/UCI/GlobalForestWatch.
- Ensure schemas match: e.g., add text analysis (nltk/spacy) for bio if needed.
- For graph analysis, integrate Neo4j by exporting connections to it (optional).
