import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# --- GOOGLE DRIVE SETUP (Service Account Auth) ---
def init_drive():
    scope = ['https://www.googleapis.com/auth/drive']
    creds_dict = st.secrets["google"]["service_account"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    gauth = GoogleAuth()
    gauth.credentials = credentials
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
        df = pd.read_csv(filename, parse_dates=['date'])

        df['date'] = pd.to_datetime(df['date']).dt.normalize()

        # Upgrade old data format
        if 'count' not in df.columns:
            df['count'] = 1

        return df, file
    else:
        return pd.DataFrame(columns=['date', 'count']), None

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

# --- MAIN APP ---
st.title("Meat-Eating Tracker")
st.sidebar.header("Tracker Settings")

if username:
    df, existing_file = load_data(username)

    # Sidebar input for logging
    selected_date = st.sidebar.date_input("Select the date")
    meat_events = st.sidebar.number_input("How many meat-eating events on this day?", min_value=0, step=1)

    if st.sidebar.button("Save"):
        selected_date = pd.to_datetime(selected_date).normalize()
        df = df[df['date'] != selected_date]  # Remove previous entry for this date
        if meat_events > 0:
            new_row = pd.DataFrame({'date': [selected_date], 'count': [meat_events]})
            df = pd.concat([df, new_row], ignore_index=True)
        save_data(df, username, existing_file)
        st.sidebar.success(f"Saved {meat_events} event(s) for {selected_date.date()}!")
        st.rerun()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        df_grouped = df.groupby('date')['count'].sum()
        
        start_date = pd.to_datetime('2025-02-10')
        all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')
        
        # Reindex to fill missing days with 1 (grey bars for unlogged days)
        df_grouped = df_grouped.reindex(all_dates, fill_value=1)  # Default is 1 (grey bar)

        today = pd.Timestamp(datetime.today().date())

        # --- Current streak ---
        if df_grouped.index[-1] == today and df_grouped[today] > 0:
            current_streak = 0
        else:
            streak = 0
            for date in reversed(df_grouped.index):
                if date > today:
                    continue
                if df_grouped[date] == 0:
                    streak += 1
                else:
                    break
            current_streak = streak

        # --- Longest streak ---
        longest_streak = 0
        streak = 0
        for val in df_grouped.values:
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
        fig, ax = plt.subplots(figsize=(10, 6))

        # Plot all days with grey bars (1 for unlogged)
        ax.bar(df_grouped.index, df_grouped.values, color='grey', alpha=0.6, label="Unlogged (Default)")

        # Plotting the meat-eating events (green bars) on top of the grey bars
        ax.bar(df_grouped.index[df_grouped > 1], df_grouped[df_grouped > 1], color='green', label="Logged Meat Events")

        ax.set_xlabel("Time")
        ax.set_ylabel("Meat-Eating Events", color='green')
        ax.tick_params(axis='y', labelcolor='green')

        # Rotate the x-axis labels for better readability
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(fig)

        # --- Download Button ---
        df_download = df_grouped.reset_index()
        df_download.columns = ['date', 'count']
        df_download['date'] = df_download['date'].dt.strftime('%Y-%d-%m')  # European format
        st.download_button(
            label="📥 Download your data as CSV",
            data=df_download.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_tracker_log.csv",
            mime='text/csv'
        )

    # --- Reset button ---
    #if st.sidebar.button("Reset Data"):
    #    df = pd.DataFrame(columns=['date', 'count'])
    #    save_data(df, username, existing_file)
    #    st.sidebar.success("Your data has been reset!")
    #    st.rerun()
else:
    st.warning("Please enter your username in the sidebar to continue.")
