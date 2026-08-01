import os
import sqlite3
from datetime import datetime
import streamlit as st
from PIL import Image

# Optional Google GenAI SDK for automated card reading
try:
  import google.generativeai as genai

  HAS_GENAI = True
except ImportError:
  HAS_GENAI = False

# Configuration & Setup
DB_FILE = "card_collection.db"
IMAGE_DIR = "card_images"
os.makedirs(IMAGE_DIR, exist_ok=True)


def init_db():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  # Create table if it doesn't exist
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
            back_path TEXT,
            date_added TEXT
        )
    """)
  # Safety check: ensure card_number column exists if table was already created previously
  cursor.execute("PRAGMA table_info(cards)")
  columns = [info[1] for info in cursor.fetchall()]
  if "card_number" not in columns:
    cursor.execute("ALTER TABLE cards ADD COLUMN card_number TEXT")

  conn.commit()
  conn.close()


init_db()

st.set_page_config(
    page_title="Elite Card Collector", page_icon="⭐", layout="wide"
)

# Custom CSS for polished layout
st.markdown("""
    <style>
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⭐ Elite Personal Card Collection")

# Sidebar Configuration for AI & Adding Cards
st.sidebar.header("Configuration & Input")
api_key = st.sidebar.text_input(
    "Gemini API Key (Optional for AI Auto-Fill)", type="password"
)

st.sidebar.divider()
st.sidebar.header("Add New Card")

front_image = st.sidebar.file_uploader(
    "Card Front Image", type=["jpg", "png", "jpeg"], key="front_upload"
)
back_image = st.sidebar.file_uploader(
    "Card Back Image", type=["jpg", "png", "jpeg"], key="back_upload"
)

ai_player, ai_sport, ai_team, ai_year, ai_num, ai_type = (
    "",
    "Baseball",
    "",
    2024,
    "",
    "Base",
)

if HAS_GENAI and api_key and front_image:
  if st.sidebar.button("✨ Auto-Detect Card Details with AI"):
    try:
      genai.configure(api_key=api_key)
      model = genai.GenerativeModel("gemini-2.5-flash")
      img = Image.open(front_image)
      prompt = (
          "Analyze this sports card image. Return strictly the following details"
          " separated by pipes (|): Player Name | Sport (Baseball, Football,"
          " or Basketball) | Team | Year | Card Number (e.g. #18 or N/A) | Card"
          " Type (e.g. Rookie, Prizm, Refractor, Base)"
      )
      response = model.generate_content([prompt, img])
      parts = [p.strip() for p in response.text.split("|")]
      if len(parts) >= 6:
        ai_player, ai_sport, ai_team, ai_year, ai_num, ai_type = (
            parts[0],
            parts[1],
            parts[2],
            int(parts[3]) if parts[3].isdigit() else 2024,
            parts[4],
            parts[5],
        )
        st.sidebar.success("AI successfully scanned card details!")
    except Exception as e:
      st.sidebar.error(f"AI Scan failed: {e}")

with st.sidebar.form("add_card_form"):
  player_name = st.text_input("Player Name", value=ai_player)
  sport = st.selectbox(
      "Sport",
      ["Baseball", "Football", "Basketball"],
      index=(
          ["Baseball", "Football", "Basketball"].index(ai_sport)
          if ai_sport in ["Baseball", "Football", "Basketball"]
          else 0
      ),
  )
  team = st.text_input("Team", value=ai_team)
  year = st.number_input(
      "Year",
      min_value=1900,
      max_value=2026,
      value=int(ai_year) if ai_year else 2024,
      step=1,
  )
  card_number = st.text_input("Card Number (e.g., #18, 154)", value=ai_num)
  card_type = st.text_input(
      "Card Type / Variant (e.g., Rookie, Refractor, Prizm)", value=ai_type
  )

  st.markdown("**Estimated Valuation Range ($)**")
  col_l, col_h = st.sidebar.columns(2)
  with col_l:
    val_low = st.number_input(
        "Low (Raw)", min_value=0.0, format="%.2f", value=0.0
    )
  with col_h:
    val_high = st.number_input(
        "High (Graded)", min_value=0.0, format="%.2f", value=0.0
    )

  submit_button = st.form_submit_button(label="Save Card to Collection")

  if submit_button:
    if not player_name or not team:
      st.error("Please provide at least a Player Name and Team.")
    else:
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
      front_path, back_path = "", ""

      if front_image:
        front_path = os.path.join(IMAGE_DIR, f"{timestamp}_front.jpg")
        with open(front_path, "wb") as f:
          f.write(front_image.getbuffer())

      if back_image:
        back_path = os.path.join(IMAGE_DIR, f"{timestamp}_back.jpg")
        with open(back_path, "wb") as f:
          f.write(back_image.getbuffer())

      conn = sqlite3.connect(DB_FILE)
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO cards (player, sport, team, year, card_number, card_type, val_low, val_high, front_path, back_path, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              player_name,
              sport,
              team,
              year,
              card_number,
              card_type,
              val_low,
              val_high,
              front_path,
              back_path,
              datetime.now().strftime("%Y-%m-%d"),
          ),
      )
      conn.commit()
      conn.close()
      st.success(f"Successfully added {player_name}!")

# Main Explorer View
st.subheader("Collection Explorer")

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("SELECT * FROM cards")
rows = cursor.fetchall()
conn.close()

if not rows:
  st.info(
      "Your collection is empty. Upload card photos and fill out details in"
      " the sidebar!"
  )
else:
  card_list = []
  for r in rows:
    # Ensure backward compatibility if old database rows had fewer columns
    card_list.append({
        "id": r[0],
        "player": r[1],
        "sport": r[2],
        "team": r[3],
        "year": r[4],
        "card_number": r[5] if len(r) > 5 and r[5] else "",
        "card_type": r[6] if len(r) > 6 and r[6] else "",
        "val_low": r[7] if len(r) > 7 and r[7] else 0.0,
        "val_high": r[8] if len(r) > 8 and r[8] else 0.0,
        "front_path": r[9] if len(r) > 9 and r[9] else "",
        "back_path": r[10] if len(r) > 10 and r[10] else "",
        "date_added": r[11] if len(r) > 11 and r[11] else "",
    })

  # Filter Layout
  f1, f2, f3 = st.columns(3)
  with f1:
    selected_sport = st.selectbox(
        "Filter by Sport", ["All"] + list(set(c["sport"] for c in card_list))
    )
  with f2:
    selected_team = st.selectbox(
        "Filter by Team", ["All"] + list(set(c["team"] for c in card_list))
    )
  with f3:
    view_mode = st.radio("View Mode", ["Polished Gallery", "Table Summary"])

  filtered_cards = card_list
  if selected_sport != "All":
    filtered_cards = [c for c in filtered_cards if c["sport"] == selected_sport]
  if selected_team != "All":
    filtered_cards = [c for c in filtered_cards if c["team"] == selected_team]

  total_low = sum(c["val_low"] for c in filtered_cards)
  total_high = sum(c["val_high"] for c in filtered_cards)

  m1, m2 = st.columns(2)
  with m1:
    st.metric("Total Cards Displayed", len(filtered_cards))
  with m2:
    st.metric(
        "Collection Value Range",
        value=f"${total_low:,.2f} — ${total_high:,.2f}",
    )

  st.divider()

  if view_mode == "Polished Gallery":
    cols_per_row = 3
    for i in range(0, len(filtered_cards), cols_per_row):
      row_cards = filtered_cards[i : i + cols_per_row]
      cols = st.columns(cols_per_row)
      for idx, card in enumerate(row_cards):
        with cols[idx]:
          with st.container():
            if card["front_path"] and os.path.exists(card["front_path"]):
              st.image(Image.open(card["front_path"]), width="stretch")
            else:
              st.warning("No image available")

            num_display = (
                f"({card['card_number']})" if card["card_number"] else ""
            )
            st.markdown(
                f"### {card['player']} {num_display}"
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

  else:
    table_data = []
    for c in filtered_cards:
      search_query = (
          f"{c['year']} {c['player']} {c['card_number']} {c['card_type']}"
      ).replace(" ", "+")
      ebay_url = (
          f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_sacat=0&LH_Sold=1&LH_Complete=1"
      )
      table_data.append({
          "Player": c["player"],
          "Sport": c["sport"],
          "Team": c["team"],
          "Year": c["year"],
          "Card #": c["card_number"],
          "Type": c["card_type"],
          "Low ($)": c["val_low"],
          "High ($)": c["val_high"],
          "Comps Link": ebay_url,
      })
    st.dataframe(table_data, width="stretch")
