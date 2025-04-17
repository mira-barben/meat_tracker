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
        df['date'] = df['date'].dt.normalize()
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

# --- Add or update a meat day ---
def update_meat_day(date, count, df):
    date = pd.to_datetime(date).normalize()
    df = df.copy()
    if date in df['date'].values:
        df.loc[df['date'] == date, 'count'] = count
    else:
        new_row = pd.DataFrame({'date': [date], 'count': [count]})
        df = pd.concat([df, new_row], ignore_index=True)
    return df

# --- MAIN APP ---
st.title("Meat-Eating Tracker")
st.sidebar.header("Tracker Settings")

if username:
    df, existing_file = load_data(username)

    # Sidebar input for logging
    meat_day_input = st.sidebar.date_input("Select the date you ate meat")
    selected_date = pd.to_datetime(meat_day_input).normalize()
    existing_count = int(df[df['date'] == selected_date]['count'].values[0]) if selected_date in df['date'].values else 0

    meat_events_input = st.sidebar.number_input(
        "How many times did you eat meat on this day?",
        min_value=0, step=1, value=existing_count
    )

    if st.sidebar.button("Save"):
        df = update_meat_day(meat_day_input, meat_events_input, df)
        save_data(df, username, existing_file)
        st.sidebar.success(f"{meat_events_input} meat-eating events saved for {meat_day_input.strftime('%d.%m.%Y')}!")
        st.rerun()

    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        start_date = pd.to_datetime('2025-02-10')  
        all_dates = pd.date_range(start=start_date, end=datetime.today(), freq='D')
        df_resampled = df['count'].reindex(all_dates, fill_value=0)

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
        plt.yticks(range(0, int(df_resampled.max()) + 2))
        plt.xlabel("Time")
        plt.ylabel("Number of Meat-Eating Events")
        plt.xticks(df_resampled.index[::max(1, len(df_resampled)//10)], 
                   df_resampled.index.strftime('%d.%m'), rotation=45)
        plt.tight_layout()
        st.pyplot(plt)

        # --- Download Button with European date format ---
        df_display = df.reset_index()
        df_display['date'] = df_display['date'].dt.strftime('%d.%m.%Y')
        st.download_button(
            label="📥 Download your data as CSV",
            data=df_display.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_tracker_log.csv",
            mime='text/csv'
        )

    # --- Reset button ---
    if st.sidebar.button("Reset Data"):
        df = pd.DataFrame(columns=['date', 'count'])
        save_data(df, username, existing_file)
        st.sidebar.success("Your data has been reset!")
        st.rerun()
else:
    st.warning("Please enter your username in the sidebar to continue.")

