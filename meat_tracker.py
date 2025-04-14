import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import json

# --- GOOGLE DRIVE SETUP ---
@st.cache_resource
def init_drive():
    gauth = GoogleAuth()

    # Manually set client config from secrets
    gauth.settings['client_config'] = json.loads(st.secrets["google"]["client_config"])

    # Try LocalWebserverAuth for environments with a browser
    try:
        gauth.LocalWebserverAuth()  # This will open a browser for authentication
    except Exception:
        gauth.CommandLineAuth()  # Fallback to command line authentication in headless environments

    return GoogleDrive(gauth)

drive = init_drive()

# --- USERNAME SETUP ---
username = st.sidebar.text_input("Enter your username to access your data")

# --- LOAD AND SAVE FUNCTIONS ---
def load_data(username):
    filename = f"{username}.csv"
    file_list = drive.ListFile({'q': f"title='{filename}' and trashed=false"}).GetList()
    if file_list:
        file = file_list[0]
        file.GetContentFile(filename)
        df = pd.read_csv(filename)
        df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.normalize()
        if df['date'].isna().sum() > 0:
            st.warning("There are invalid date values in your data.")
        return df, file
    else:
        return pd.DataFrame(columns=['date']), None

def save_data(df, username, existing_file):
    filename = f"{username}.csv"
    df.to_csv(filename, index=False)
    if existing_file:
        existing_file.SetContentFile(filename)
        existing_file.Upload()
    else:
        new_file = drive.CreateFile({'title': filename})
        new_file.SetContentFile(filename)
        new_file.Upload()

def add_meat_day(date, df):
    date = pd.to_datetime(date).normalize()
    new_row = pd.DataFrame({'date': [date]})
    return pd.concat([df, new_row], ignore_index=True)

# --- MAIN APP ---
st.title("Meat-Eating Tracker")
st.sidebar.header("Tracker Settings")

if username:
    df, existing_file = load_data(username)

    # Sidebar input for logging
    meat_day_input = st.sidebar.date_input("Select the date you ate meat")
    meat_events_input = st.sidebar.number_input("How many times did you eat meat on this day?", min_value=0, step=1)

    if st.sidebar.button("Log"):
        for _ in range(meat_events_input):
            df = add_meat_day(meat_day_input, df)
        save_data(df, username, existing_file)
        st.sidebar.success(f"{meat_events_input} meat-eating events added for {meat_day_input}!")
        st.rerun()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df_resampled = df.resample('D').size()

        start_date = pd.to_datetime('2025-02-10')  
        all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')
        df_resampled = df_resampled.reindex(all_dates, fill_value=0)

        today = pd.Timestamp(datetime.today().date())

        # --- Current streak ---
        if df_resampled.index[-1] == today and df_resampled[today] > 0:
            current_streak = 0
        else:
            streak = 0
            for date in reversed(df_resampled.index):
                if date > today:
                    continue
                if df_resampled[date] == 0:
                    streak += 1
                else:
                    break
            current_streak = streak

        # --- Longest streak ---
        longest_streak = 0
        streak = 0
        for val in df_resampled.values:
            if val == 0:
                streak += 1
                longest_streak = max(longest_streak, streak)
            else:
                streak = 0

        col1, col2 = st.columns(2)
        with col1:
            st.metric("🥗 Days without meat", f"{current_streak} days")
        with col2:
            st.metric("🏆 Longest streak", f"{longest_streak} days")

        # --- Plotting (Bar Chart) ---
        plt.figure(figsize=(10, 6))
        plt.bar(df_resampled.index, df_resampled.values, color='green')
        plt.yticks(range(0, int(df_resampled.max()) + 1))
        plt.xlabel("Time")
        plt.ylabel("Number of Meat-Eating Events")
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(plt)

        # --- Download Button ---
        st.download_button(
            label="📥 Download your data as CSV",
            data=df.reset_index().to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_log.csv",
            mime='text/csv'
        )

    # --- Reset button ---
    if st.sidebar.button("Reset Data"):
        df = pd.DataFrame(columns=['date'])
        save_data(df, username, existing_file)
        st.sidebar.success("Your data has been reset!")
        st.rerun()
else:
    st.warning("Please enter your username in the sidebar to continue.")
