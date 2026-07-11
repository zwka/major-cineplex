# Major Cineplex Seat Scraper

This design document outlines the implementation plan for scraping movie showtimes and seat occupancy from Major Cineplex cinemas, reframed using the `/office-hours` (Builder Mode) workflow.

## Office Hours Reframing (Builder Mode)

- **Core Experience**: A reliable, automated data pipeline and a **Premium Web Dashboard** that extracts and visualizes seat booking density across Major Cineplex cinemas.
- **Simplest Version**: A Python CLI scraper storing data in SQLite, combined with a Next.js Web Dashboard for data visualization.
- **Technical Risks**: 
  1. **Anti-bot mechanisms**: The booking system may employ Cloudflare, CAPTCHAs, or rate limiting.
  2. **Data Scale**: Rendering thousands of showtimes on the dashboard efficiently.

## Proposed Architecture

### 1. Scraper Engine (Python)
- **Tooling**: `Playwright` for Python.
- **Features**: 
  - Live progress bar using `rich` or `tqdm` to show scraping progress.
  - End-of-run summary report (success/failure rates).
  - Handles duplicates using SQLite `INSERT OR REPLACE`.

### 2. Database & Data Model
- **Database**: Python's built-in `sqlite3` (`major_cineplex.db`).
- **Schema**:
  - `cinemas` (id, name, url)
  - `movies` (id, title)
  - `showtimes` (id, cinema_id, movie_id, show_date, show_time, url)
  - `seat_occupancy` (showtime_id, total_seats, sold_seats, available_seats, scraped_at)

### 3. CSV Export
- Generates timestamped CSV reports (e.g., `major_cineplex_2026-07-11.csv`) and saves them in a dedicated `reports/` directory.

### 4. Web Dashboard (Next.js)
- **Framework**: Next.js (App Router) to directly read the local `major_cineplex.db` SQLite file via Server Components.
- **Styling**: Premium Vanilla CSS (Dynamic, Glassmorphism, Micro-animations) as per design guidelines. No Tailwind.
- **Features**:
  - High-level stats overview (Total seats sold, occupancy rate).
  - Data table/charts to visualize movie performance.

We will build a Python-based scraping application.

### 1. Scraper Engine
- Use `Playwright` for Python to handle dynamic content, JavaScript execution, and bypass basic scraping protections.
- Implement a 3-step navigation flow:
  1. Scrape the list of all cinemas from `https://www.majorcineplex.com/cinema/`.
  2. For each cinema, navigate to its showtime page and scrape the list of movies and available showtimes.
  3. For each showtime, "click" into the booking page to read the seat map and calculate `seats sold`.

### 2. Database & Data Model
- Use Python's built-in `sqlite3` to store the scraped data.
- **Schema**:
  - `cinemas` (id, name, url)
  - `movies` (id, title)
  - `showtimes` (id, cinema_id, movie_id, show_date, show_time, url)
  - `seat_occupancy` (showtime_id, total_seats, sold_seats, available_seats, scraped_at)

### 3. Duplicate Handling
- We will enforce `UNIQUE` constraints in SQLite (e.g., on `cinema_id`, `movie_id`, `show_date`, `show_time`).
- Use `INSERT OR REPLACE` (or `INSERT ... ON CONFLICT DO UPDATE`) to gracefully handle duplicates and update the seat counts if they change.

### 4. CSV Export
- Implement an `--export` CLI flag that executes a `JOIN` query across the tables and uses Python's `csv` module to write the structured output to `major_cineplex_data.csv`.

## Verification Plan

### Manual Verification
1. Run the scraper on a single cinema (e.g., Paragon Cineplex) to verify it successfully navigates to the seat map and extracts the correct number of seats.
2. Manually compare the scraped SQLite data with the live website for 2-3 showtimes.
3. Run the script twice to ensure duplicate handling works correctly (no duplicate rows created, existing rows updated).
4. Run the `--export` command and verify the CSV structure and data integrity.
