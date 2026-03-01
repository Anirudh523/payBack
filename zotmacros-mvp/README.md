# ZotMacros MVP

MyFitnessPal-style MVP for UCI Dining: pick restaurant, date, meal period, and station; view items with calories and protein; log items to a planner; see remaining calories/protein vs goals; get recommended item combos that fit remaining calories and maximize protein.

Uses **AnteaterAPI** dining endpoints only (no scraping).

## Setup

1. **Create and activate a virtual environment**

   ```bash
   cd zotmacros-mvp
   python3 -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**

   ```bash
   streamlit run app.py
   ```

## Usage

- Choose **Restaurant**: Anteatery or Brandywine.
- Pick a **Date** (default: today).
- Set **Calories goal** (default 2000) and **Protein goal** (default 150 g).
- Select **Meal period** and **Station**, then **Add** dishes to your log.
- Use **Planner** to remove items or clear the log.
- Click **Recommend** to see up to 5 combos that fit your remaining calories and prioritize protein.

## API

- `GET https://anteaterapi.com/v2/rest/dining/restaurants` — stations list
- `GET https://anteaterapi.com/v2/rest/dining/restaurantToday?id=<id>&date=<YYYY-MM-DD>` — periods + stationToDishes
- `GET https://anteaterapi.com/v2/rest/dining/dishes/batch?ids=<comma-separated>` — dish details (including nutrition)

Restaurant IDs: `anteatery`, `brandywine`.
