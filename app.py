card_list = []
    for r in rows:
      # Safely convert valuations to floats, defaulting to 0.0 if anything is text/null
      try:
        v_low = float(r[7]) if r[7] is not None else 0.0
      except (ValueError, TypeError):
        v_low = 0.0

      try:
        v_high = float(r[8]) if r[8] is not None else 0.0
      except (ValueError, TypeError):
        v_high = 0.0

      card_list.append({
          "id": r[0],
          "player": r[1],
          "sport": r[2],
          "team": r[3],
          "year": r[4],
          "card_number": r[5],
          "card_type": r[6],
          "val_low": v_low,
          "val_high": v_high,
          "front_path": r[7],  # Note: ensure index matches your table schema
          "date_added": r[8],
      })
