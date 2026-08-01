import os
import sqlite3
from datetime import datetime
import streamlit as st
from PIL import Image

try:
  import google.generativeai as genai

  HAS_GENAI = True
except ImportError:
  HAS_GENAI = False

DB_FILE = "card_collection.db"
IMAGE_DIR = "card_images"
os.makedirs(IMAGE_DIR, exist_ok=True)


def init_db():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT,
            sport TEXT,
            team TEXT,
            year INTEGER,
            card_number TEXT,
            card_type TEXT,
            val_low REAL,
            val_high REAL,
            front_path TEXT,
            date_added TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()

st.set_page_config(
    page_title="AI Sports Card Vault", page_icon="⚡", layout="wide"
)

st.title("⚡ AI Sports Card Vault & Batch Processor")

# Sidebar Configuration for API Key
st.sidebar.header("🔑 AI Configuration")
api_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    help="Required for autonomous photo extraction.",
)

# Main Navigation Tabs
tab_upload, tab_vault = st.tabs(
    ["📥 Batch Upload & AI Processing", "🏛️ Card Vault & Categories"]
)

with tab_upload:
  st.subheader("Drop Your Card Photos")
  st.markdown(
      "Upload one or multiple card photos. The AI will automatically extract"
      " the player, sport, team, year, and card type, then log it into your"
      " vault instantly."
  )

  uploaded_files = st.file_uploader(
      "Choose card images...",
      type=["jpg", "png", "jpeg"],
      accept_multiple_files=True,
  )

  if uploaded_files:
    if not api_key:
      st.warning(
          "⚠️ Please enter your Gemini API key in the sidebar to enable AI"
          " processing."
      )
    else:
      if st.button("🚀 Process All Cards with AI"):
        genai.configure(api_key=api_key)
        # Using gemini-2.5-flash as an efficient multimodal engine
        model = genai.GenerativeModel("gemini-2.5-flash")

        progress_bar = st.progress(0)
        total_files = len(uploaded_files)

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        for idx, uploaded_file in enumerate(uploaded_files):
          try:
            img = Image.open(uploaded_file)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            front_path = os.path.join(IMAGE_DIR, f"{timestamp}_{idx}.jpg")
            img.save(front_path)

            prompt = (
                "Analyze this sports card image. Return strictly and only the"
                " following details separated by vertical pipes (|): Player"
                " Name | Sport (Baseball, Football, or Basketball) | Team |"
                " Year | Card Number (e.g. #18 or N/A) | Card Type (e.g."
                " Rookie, Prizm, Refractor, Base). Do not include any other"
                " text."
            )

            response = model.generate_content([prompt, img])
            parts = [p.strip() for p in response.text.split("|")]

            if len(parts) >= 6:
              player = parts[0]
              sport = parts[1] if parts[1] in ["Baseball", "Football", "Basketball"] else "Baseball"
              team = parts[2]
              year = int(parts[3]) if parts[3].isdigit() else 2024
              card_number = parts[4]
              card_type = parts[5]
            else:
              player, sport, team, year, card_number, card_type = (
                  "Unknown Player",
                  "Baseball",
                  "Unknown Team",
                  2024,
                  "N/A",
                  "Base",
              )

            # Default baseline valuations (adjustable later)
            val_low, val_high = 5.0, 25.0

            cursor.execute(
                """
                            INSERT INTO cards (player, sport, team, year, card_number, card_type, val_low, val_high, front_path, date_added)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                (
                    player,
                    sport,
                    team,
                    year,
                    card_number,
                    card_type,
                    val_low,
                    val_high,
                    front_path,
                    datetime.now().strftime("%Y-%m-%d"),
                ),
            )
            conn.commit()

          except Exception as e:
            st.error(f"Error processing {uploaded_file.name}: {e}")

          progress_bar.progress((idx + 1) / total_files)

        conn.close()
        st.success(
            f"🎉 Successfully processed and stored {total_files} cards into"
            " your vault!"
        )

with tab_vault:
  st.subheader("Your Organized Collection")

  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("SELECT * FROM cards")
  rows = cursor.fetchall()
  conn.close()

  if not rows:
    st.info(
        "Your vault is currently empty. Head over to the 'Batch Upload' tab to"
        " start scanning cards!"
    )
  else:
    card_list = []
    for r in rows:
      card_list.append({
          "id": r[0],
          "player": r[1],
          "sport": r[2],
          "team": r[3],
          "year": r[4],
          "card_number": r[5],
          "card_type": r[6],
          "val_low": r[7],
          "val_high": r[8],
          "front_path": r[9],
          "date_added": r[10],
      })

    # Dynamic Filter Controls
    c1, c2, c3 = st.columns(3)
    with c1:
      all_sports = ["All"] + list(set(c["sport"] for c in card_list))
      selected_sport = st.selectbox("Filter by Sport", all_sports)
    with c2:
      all_teams = ["All"] + list(set(c["team"] for c in card_list))
      selected_team = st.selectbox("Filter by Team", all_teams)
    with c3:
      all_types = ["All"] + list(set(c["card_type"] for c in card_list))
      selected_type = st.selectbox("Filter by Card Type", all_types)

    # Apply filters
    filtered = card_list
    if selected_sport != "All":
      filtered = [c for c in filtered if c["sport"] == selected_sport]
    if selected_team != "All":
      filtered = [c for c in filtered if c["team"] == selected_team]
    if selected_type != "All":
      filtered = [c for c in filtered if c["card_type"] == selected_type]

    # Metrics overview
    t_low = sum(c["val_low"] for c in filtered)
    t_high = sum(c["val_high"] for c in filtered)

    m1, m2 = st.columns(2)
    with m1:
      st.metric("Filtered Cards Shown", len(filtered))
    with m2:
      st.metric(
          "Estimated Value Range", value=f"${t_low:,.2f} — ${t_high:,.2f}"
      )

    st.divider()

    # Visual Gallery Grid Layout
    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
      row_cards = filtered[i : i + cols_per_row]
      cols = st.columns(cols_per_row)
      for idx, card in enumerate(row_cards):
        with cols[idx]:
          if card["front_path"] and os.path.exists(card["front_path"]):
            st.image(Image.open(card["front_path"]), width="stretch")
          else:
            st.warning("Image missing")

          st.markdown(
              f"### {card['player']} `({card['card_number']})`"
          )
          st.caption(
              f"**{card['sport']}** | {card['team']} | {card['year']}"
          )
          st.markdown(f"🏷️ Type:")
          st.markdown(
              f"💰 **Value:** ${card['val_low']:,.2f} –"
              f" ${card['val_high']:,.2f}"
          )

          search_query = (
              f"{card['year']} {card['player']} {card['card_number']}"
              f" {card['card_type']}"
          ).replace(" ", "+")
          ebay_url = (
              f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_sacat=0&LH_Sold=1&LH_Complete=1"
          )
          st.markdown(
              f"🔗 [Market Comps (eBay Sold)]({ebay_url})",
              unsafe_allow_html=True,
          )
          st.divider()
