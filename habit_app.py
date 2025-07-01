import streamlit as st
import datetime
import pandas as pd
import json
import os
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import matplotlib.pyplot as plt
import dayplot as dp
import matplotlib.pyplot as plt


# Starte App im Terminal mit:
# streamlit run habit_app.py

# --- Login-Konfiguration ---

# Userdaten aus der YAML-Datei laden
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

# Authenticator-Objekt erstellen
authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# Login-Widget anzeigen (siehe: https://github.com/mkhorasani/Streamlit-Authenticator?ref=blog.streamlit.io )
try:
    authenticator.login()
except Exception as e:
    st.error(e)


# --- Datenpersistenz ---
DATA_FILE = "habit_data.json"

def load_json_file(filepath, default=None):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json_file(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Datenpersistenz-Wrapper ---

def save_all_data(all_data):
    save_json_file(DATA_FILE, all_data)

def get_user_data(username):
    all_data = load_json_file(DATA_FILE, {})
    return all_data.get(username, {"habits": [], "done_by_date": {}})

def save_user_data(username, user_data):
    all_data = load_json_file(DATA_FILE, {})
    all_data[username] = user_data
    save_all_data(all_data)

# --- Haupt-UI für eingeloggte Nutzer ---
def main_app(name, username):
    # st.success(f"Willkommen, {name}!")
    # st.toast(f"Willkommen, {name}!")#, icon="✅") , icon="⚠️" , icon="❌"
    
    # Userdaten initialisieren
    if 'habits' not in st.session_state or 'done_by_date' not in st.session_state:
        user_data = get_user_data(username)
        st.session_state['habits'] = user_data.get('habits', [])
        st.session_state['done_by_date'] = {date: set(status) for date, status in user_data.get('done_by_date', {}).items()}
    
    # aktuellen Zustand speichern    
    def persist():
        save_user_data(username, {
            'habits': st.session_state['habits'],
            'done_by_date': {date: list(status) for date, status in st.session_state['done_by_date'].items()}
        })    

    # Meldungen beim Anlegen neuer Gewohnheiten
    query_params = st.query_params
    if 'added' in query_params:
        st.toast(f'{query_params["added"]} hinzugefügt!', icon="✅") 
        st.query_params.clear()
    if 'duplicate' in query_params:
        st.toast(f'{query_params["duplicate"]} existiert bereits! Bitte gib eine neue Gewohnheit ein.', icon="❌") 
        st.query_params.clear()

    # heutiges Datum
    selected_date = datetime.date.today()
    selected_date_str = selected_date.isoformat()
    
    # Standard: heute
    if 'selected_date' not in st.session_state:
        st.session_state['selected_date'] = datetime.date.today()

    selected_date = st.session_state['selected_date']
    selected_date_str = selected_date.isoformat()
    
    # Gewohnheiten als erledigt markieren
    # st.subheader(f'Deine Gewohnheiten am {selected_date.strftime("%d.%m.%Y")}:')
    st.markdown(f'#### Deine Gewohnheiten am {selected_date.strftime("%d.%m.%Y")}:')
    if st.session_state['habits']:
        if selected_date_str not in st.session_state['done_by_date']:
            st.session_state['done_by_date'][selected_date_str] = set()
        for i, habit in enumerate(st.session_state['habits']):
            done = i in st.session_state['done_by_date'][selected_date_str]

            cols = st.columns([6, 1])
            with cols[0]:
                if not done:
                    if st.button(f"{habit}", key=f'done_{i}_{selected_date_str}', type="secondary"):
                        st.session_state['done_by_date'][selected_date_str].add(i)
                        st.rerun()
                else:
                    if st.button(f"{habit}", key=f'undone_{i}_{selected_date_str}', type="primary"):
                        st.session_state['done_by_date'][selected_date_str].discard(i)
                        st.rerun()
            with cols[1]:
                if st.button("🗑️", key=f'delete_{i}'):
                    # Entferne Habit und alle zugehörigen Einträge in done_by_date
                    st.session_state['habits'].pop(i)
                    for date in list(st.session_state['done_by_date'].keys()):
                        st.session_state['done_by_date'][date] = {j if j < i else j-1 for j in st.session_state['done_by_date'][date] if j != i}
                    st.rerun()
    else:
        st.info('Noch keine Gewohnheiten eingetragen.')

    # 2. Datumsauswahl
    selected_date = st.date_input('Datum auswählen:', st.session_state['selected_date'], label_visibility='collapsed')
    if selected_date != st.session_state['selected_date']:
        st.session_state['selected_date'] = selected_date
        st.rerun()
    selected_date_str = selected_date.isoformat()

    # --- Contribution-Chart: Pro Gewohnheit ein Kalender-Chart (1 Jahr) ---
    if st.session_state['habits']:
        st.markdown('---')
        for i, habit in enumerate(st.session_state['habits']):
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=365)
            habit_dates = pd.date_range(start=start_date, end=end_date)
            df = pd.DataFrame({'Datum': habit_dates})
            df['Datum_str'] = df['Datum'].dt.date.astype(str)
            df['Erledigt'] = df['Datum_str'].map(lambda d: int(i in st.session_state['done_by_date'].get(d, set())))
                        
            # Kalender-Heatmap mit Matplotlib (siehe https://python-graph-gallery.com/calendar-heatmaps-with-python-and-matplotlib/)
            fig_mp, ax_mp = plt.subplots(figsize=(15, 6), dpi=300)
            dp.calendar(
                dates=df["Datum_str"],
                values=df["Erledigt"],
                start_date=start_date,
                end_date=end_date,
                ax=ax_mp,
                cmap='Reds' 
            )
            # labels
            text_args = dict(x=-2, y=-2, size=20, color="black")
            ax_mp.text(s=habit, **text_args)

            st.pyplot(fig_mp)

    # Eingabe für neue Gewohnheit
    if 'new_habit' not in st.session_state:
        st.session_state['new_habit'] = ''

    def submit():
        st.session_state['new_habit'] = st.session_state['habit_input']
        st.session_state['habit_input'] = ''

    st.text_input('', key='habit_input', 
                      placeholder='Neue Gewohnheit hinzufügen:', 
                      label_visibility='collapsed', 
                      on_change=submit)
    
    if st.session_state['new_habit'] != '':
        if st.session_state['new_habit'] not in st.session_state['habits']:
            st.session_state['habits'].append(st.session_state['new_habit'])
            st.query_params["added"] = st.session_state['new_habit']
            st.session_state['new_habit'] = ''
            st.rerun()
        else:
            st.query_params["duplicate"] = st.session_state['new_habit']
            st.session_state['new_habit'] = ''
            st.rerun()

    # Nach jeder Änderung speichern
    if st.session_state['habits'] or st.session_state['done_by_date']:
        persist()


# --- Steuerlogik: Was wird angezeigt? ---
# App-Inhalt anzeigen, wenn der Benutzer eingeloggt ist
if st.session_state.get('authentication_status'):
    main_app(st.session_state.get('name', ''), st.session_state.get('username', ''))
    authenticator.logout('Logout', 'main')
elif st.session_state.get('authentication_status') == False:
    st.error('Benutzername/Passwort ist falsch')

