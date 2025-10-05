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

    selected_date = st.sidebar.date_input("Select the date")
    meat_events = st.sidebar.number_input("How many meat-eating events on this day?", min_value=0, step=1)

    if st.sidebar.button("Save"):
        selected_date = pd.to_datetime(selected_date).normalize()
        df = df[df['date'] != selected_date]
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
        df_grouped = df_grouped.reindex(all_dates)
        df_grouped_filled = df_grouped.fillna(1)

        today = pd.Timestamp(datetime.today().date())

        if 'archived_achievements' not in st.session_state:
            st.session_state.archived_achievements = []

        longest_streak = current_streak = 0
        for val in df_grouped.values:
            if val == 0:
                current_streak += 1
                longest_streak = max(longest_streak, current_streak)
            else:
                current_streak = 0

        col1, col2 = st.columns(2)
        col1.metric("🥗 Days without meat", f"{current_streak} days")
        col2.metric("🏆 Longest streak", f"{longest_streak} days")

# --- Define All Streak Achievements ---
        streak_achievements = {
            100: "100-day streak",
            111: "111-day streak",
            125: "125-day streak",
            150: "150-day streak",
            175: "175-day streak",
            183: "183-day streak",
            200: "200-day streak",
            222: "222-day streak",
            250: "250-day streak",
        }

        active_achievements = []
        negative_message = None

        # --- Meat-Free Calendar Weeks ---
        df_zero_filled = df_grouped.fillna(999)
        calendar_weeks = df_zero_filled.groupby([df_zero_filled.index.isocalendar().year, df_zero_filled.index.isocalendar().week])
        meat_free_weeks = 0
        for _, week in calendar_weeks:
            if len(week) == 7 and all(week == 0):
                meat_free_weeks += 1
        
        # --- Initialize Achievements ---
        active_achievements = []
        negative_message = None

        # --- Meat-Free Calendar Weeks ---
        df_zero_filled = df_grouped.fillna(999)
        calendar_weeks = df_zero_filled.groupby([df_zero_filled.index.isocalendar().year, df_zero_filled.index.isocalendar().week])
        meat_free_weeks = 0
        for _, week in calendar_weeks:
            if len(week) == 7 and all(week == 0):
                meat_free_weeks += 1

        # --- Handle Meat-Free Week Achievement (single dynamic) ---
        if meat_free_weeks > 0:
            week_achievement_name = f"{meat_free_weeks}-week meat-free streak"
            active_achievements.append(week_achievement_name)

        # --- Add only the highest unlocked streak achievement ---
        unlocked_streaks = [day for day in streak_achievements if longest_streak >= day]
        if unlocked_streaks:
            highest = max(unlocked_streaks)
            active_achievements.append(streak_achievements[highest])

        # --- Handle Negative Achievement ---
        if df_grouped[df_grouped > 0].index.max() == today:
            active_achievements.clear()
            negative_message = """
                <div style='background-color:#f8d7da;padding:20px;border-radius:10px;border-left:5px solid red;'>
                    <strong>🚨 Oh no! You ate meat after reaching such a nice streak! 👎</strong><br>
                    <strong>💚 Don't worry though, it's just a small setback.</strong><br>
                    <strong>🐄 Get right back to saving animals and unlock your achievements again!</strong>
                </div>
            """

        # --- Display Active Achievements ---
        if active_achievements:
            st.markdown("### Active Achievement")
            for achievement in active_achievements:
                if achievement == "100-day streak":
                    st.markdown("""
                        <div style='background-color:#d0ebff;padding:20px;border-radius:10px;border-left:5px solid #339af0;'>
                            <strong>🌈 100 meat-free days! You're on another level. 🐄🐖🐓🐑🐟 Thank you from the animals.</strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif achievement == "111-day streak":
                    st.markdown("""
                        <div style='background-color:#d3f9d8;padding:20px;border-radius:10px;border-left:5px solid #69db7c;'>
                            <strong>🌀 111 days! A magical repeating streak. The universe approves! ✨</strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif achievement == "125-day streak":
                    st.markdown("""
                        <div style='background-color:#fff3bf;padding:20px;border-radius:10px;border-left:5px solid #ffd43b;'>
                            <strong>💫 125 days! Your journey is inspiring. Every animal is cheering you on!/strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif achievement == "150-day streak":
                    st.markdown("""
                        <div style='background-color:#ffe0b2;padding:20px;border-radius:10px;border-left:5px solid #ffa94d;'>
                            <strong>🔥 150 days! That’s dedication. The planet and animals thank you. 🌍🐷</strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif achievement == "175-day streak":
                    st.markdown("""
                        <div style='background-color:#ffc9c9;padding:20px;border-radius:10px;border-left:5px solid #ff6b6b;'>
                            <strong>🌻 175 days meat-free! Your compassion is amazing 🌿</strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif achievement == "183-day streak":
                    st.markdown("""
                        <div style='background-color:#e5dbff;padding:20px;border-radius:10px;border-left:5px solid #9775fa;'>
                            <strong>💚183 Täg - es haubs Jahr! Wi cool isch ds!! </strong><br>
                            <strong>💚I fröie mi so fescht bisch am dürezieh u i bi mega stouz uf di!💚</strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif achievement == "222-day streak":
                    st.balloons()
                    st.markdown("""
                        <div style='background-color:#f3d9fa;padding:20px;border-radius:10px;border-left:5px solid #da77f2;'>
                            <strong>🎯 222 Täg! Ds mues natürlech o spezieu füreghobe wärde😌 🐄🐖🐓</strong>
                        </div>
                    """, unsafe_allow_html=True)
                elif "week meat-free streak" in achievement:
                    week_count = achievement.split('-')[0]
                    st.markdown(f"""
                        <div style='background-color:#d4edda;padding:20px;border-radius:10px;border-left:5px solid green;'>
                            <strong>🌿 {week_count} full calendar weeks meat-free! Outstanding!</strong><br>
                            <strong>💚 Keep saving lives every week. 🐄🐖🐓🐟</strong>
                        </div>
                    """, unsafe_allow_html=True)

        # --- Display Negative Message ---
        if negative_message:
            st.markdown(negative_message, unsafe_allow_html=True)

        # Identify Unlogged Days
        unlogged_days = df_grouped[df_grouped.isna()].index
        unlogged_df = pd.DataFrame(unlogged_days, columns=["Unlogged Dates"])
        unlogged_df["Unlogged Dates"] = unlogged_df["Unlogged Dates"].dt.strftime("%Y-%m-%d")

        st.sidebar.markdown("---")
        st.sidebar.subheader("Bulk add No-Meat Days")
        bulk_dates = st.sidebar.multiselect(
            "Select multiple unlogged dates to mark as meat-free (0 events):",
            options=unlogged_days,
            format_func=lambda d: d.strftime("%Y-%m-%d")
        )

        if st.sidebar.button("Save selected days as 0"):
            for date in bulk_dates:
                date = pd.to_datetime(date).normalize()
                df = df[df['date'] != date]
                new_row = pd.DataFrame({'date': [date], 'count': [0]})
                df = pd.concat([df, new_row], ignore_index=True)
            save_data(df, username, existing_file)
            st.sidebar.success(f"Saved {len(bulk_dates)} zero-event day(s)!")
            st.rerun()

        # Plotting
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.bar(df_grouped_filled.index, df_grouped_filled.values, color='grey', alpha=0.6, label="Unlogged Day")
        ax.bar(df_grouped.index[df_grouped > 0], df_grouped[df_grouped > 0], color='green', label="Logged Meat Eating")
        ax.set_xlabel("Time")
        ax.set_ylabel("Meat-Eating Events")

        weekly_ticks = pd.date_range(start=df_grouped_filled.index[0], end=df_grouped_filled.index[-1], freq='W-MON')
        ax.set_xticks(weekly_ticks)
        ax.set_xticklabels(weekly_ticks.strftime('%Y-%m-%d'), rotation=45, ha='right')
        ax.tick_params(axis='x', which='major', length=7, width=2, color='black')
        ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax.legend()
        plt.tight_layout()
        st.pyplot(fig)

        # Download
        df_download = df_grouped.reset_index()
        df_download.columns = ['date', 'count']
        df_download['date'] = df_download['date'].dt.strftime('%Y-%d-%m')
        st.download_button(
            label="📥 Download your data as CSV",
            data=df_download.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_meat_tracker_log.csv",
            mime='text/csv'
        )
else:
    st.warning("Please enter your username in the sidebar to continue.")






