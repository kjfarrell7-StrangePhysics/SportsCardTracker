import os
import sqlite3
from datetime import datetime
import streamlit as st
from PIL import Image

# Configuration & Setup
DB_FILE = "card_collection.db"
IMAGE_DIR = "card_images"

os.makedirs(IMAGE_DIR, exist_ok=True)


# Database Initialization (Updated to support valuation ranges)
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
            card_type TEXT,
            val_low REAL,
            val_high REAL,
            front_path TEXT,
            back_path TEXT,
            date_added TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()

st.set_page_config(
    page_title="Personal Card Tracker", page_icon="🃏", layout="wide"
)

st.title("🃏 Personal Card Collection Tracker")

# Sidebar: Add Card Form
st.sidebar.header("Add New Card")
with st.sidebar.form("add_card_form", clear_on_submit=True):
  player_name = st.text_input("Player Name")
  sport = st.selectbox("Sport", ["Baseball", "Football", "Basketball"])
  team = st.text_input("Team")
  year = st.number_input(
      "Year", min_value=1900, max_value=2026, value=2024, step=1
  )
  card_type = st.text_input("Card Type (e.g., Rookie, Base, Refractor, Auto)")

  st.markdown("**Estimated Valuation Range ($)**")
  col_l, col_h = st.sidebar.columns(2)
  with col_l:
    val_low = st.number_input(
        "Low (Raw/Ungraded)", min_value=0.0, format="%.2f", value=0.0
    )
  with col_h:
    val_high = st.number_input(
        "High (Graded/Mint)", min_value=0.0, format="%.2f", value=0.0
    )

  front_image = st.file_uploader(
      "Card Front", type=["jpg", "png", "jpeg"], key="front"
  )
  back_image = st.file_uploader(
      "Card Back", type=["jpg", "png", "jpeg"], key="back"
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

      # Insert into Database
      conn = sqlite3.connect(DB_FILE)
      cursor = conn.cursor()
      cursor.execute(
          """
                INSERT INTO cards (player, sport, team, year, card_type, val_low, val_high, front_path, back_path, date_added)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              player_name,
              sport,
              team,
              year,
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

# Main Area: Filter & View Collection
st.subheader("Collection Explorer")

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()
cursor.execute("SELECT * FROM cards")
rows = cursor.fetchall()
conn.close()

if not rows:
  st.info("Your collection is currently empty. Use the sidebar to add cards!")
else:
  # Convert to structured data/list for filtering
  card_list = []
  for r in rows:
    card_list.append({
        "id": r[0],
        "player": r[1],
        "sport": r[2],
        "team": r[3],
        "year": r[4],
        "card_type": r[5],
        "val_low": r[6],
        "val_high": r[7],
        "front_path": r[8],
        "back_path": r[9],
        "date_added": r[10],
    })

  # Filters
  col1, col2, col3 = st.columns(3)
  with col1:
    selected_sport = st.selectbox(
        "Filter by Sport", ["All"] + list(set(c["sport"] for c in card_list))
    )
  with col2:
    selected_team = st.selectbox(
        "Filter by Team", ["All"] + list(set(c["team"] for c in card_list))
    )
  with col3:
    view_mode = st.radio("View Mode", ["Grid Gallery", "Table Summary"])

  # Apply Filters
  filtered_cards = card_list
  if selected_sport != "All":
    filtered_cards = [c for c in filtered_cards if c["sport"] == selected_sport]
  if selected_team != "All":
    filtered_cards = [c for c in filtered_cards if c["team"] == selected_team]

  # Calculate running total valuation ranges
  total_low = sum(c["val_low"] for c in filtered_cards)
  total_high = sum(c["val_high"] for c in filtered_cards)

  # Display metrics header
  mcol1, mcol2 = st.columns(2)
  with mcol1:
    st.metric(label="Filtered Cards Count", value=len(filtered_cards))
  with mcol2:
    st.metric(
        label="Estimated Collection Value Range",
        value=f"${total_low:,.2f} — ${total_high:,.2f}",
    )

  st.divider()

  if view_mode == "Grid Gallery":
    cols_per_row = 3
    for i in range(0, len(filtered_cards), cols_per_row):
      row_cards = filtered_cards[i : i + cols_per_row]
      cols = st.columns(cols_per_row)
      for idx, card in enumerate(row_cards):
        with cols[idx]:
          if card["front_path"] and os.path.exists(card["front_path"]):
            st.image(Image.open(card["front_path"]), use_container_width=True)
          else:
            st.warning("No image available")

          st.markdown(f"**{card['player']}** ({card['year']})")
          st.caption(
              f"{card['sport']} | {card['team']} | Type: {card['card_type']}"
          )
          st.markdown(
              f"💰 **Value Range:** ${card['val_low']:,.2f} –"
              f" ${card['val_high']:,.2f}"
          )

          # Quick search generation link for eBay Sold listings
          search_query = (
              f"{card['year']} {card['player']} {card['card_type']}"
          ).replace(" ", "+")
          ebay_url = (
              f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_sacat=0&LH_Sold=1&LH_Complete=1"
          )
          st.markdown(
              f"🔗 [Check Market Comps (eBay Sold)]({ebay_url})",
              unsafe_allow_html=True,
          )
          st.divider()

  else:
    # Table Summary View
    table_data = []
    for c in filtered_cards:
      search_query = (f"{c['year']} {c['player']} {c['card_type']}").replace(
          " ", "+"
      )
      ebay_url = (
          f"https://www.ebay.com/sch/i.html?_nkw={search_query}&_sacat=0&LH_Sold=1&LH_Complete=1"
      )
      table_data.append({
          "Player": c["player"],
          "Sport": c["sport"],
          "Team": c["team"],
          "Year": c["year"],
          "Type": c["card_type"],
          "Valuation Low ($)": c["val_low"],
          "Valuation High ($)": c["val_high"],
          "Market Check": ebay_url,
          "Added": c["date_added"],
      })

    st.dataframe(table_data, use_container_width=True)
