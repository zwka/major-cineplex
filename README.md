# Major Cineplex Seat Scraper & Web Dashboard

An automated, high-performance data extraction pipeline and web visualization dashboard for Major Cineplex seat booking analytics.

---

## Features

* **English-Localized Crawl**: Automatically forces an English language session natively at the server level, ensuring all extracted movies, showtimes, and cinema names are saved in English.
* **Concurrent Async Architecture**: Utilizes Playwright's `APIRequestContext` with custom semaphore controls to fetch and parse **all 193 cinemas** and all active daily showtimes in parallel under 50 seconds.
* **Automated CSV Reports**: Generates a timestamped CSV dataset in the `reports/` folder at the end of every scraper run.
* **Premium Web Dashboard**: A Next.js App Router visualization dashboard that queries the SQLite database directly, styled with glassmorphism, responsive mobile layouts, color-coded seat occupancy rates, sorting, and dynamic dropdown filter controls.

---

## Tech Stack
* **Scraper**: Python 3, `playwright`, `BeautifulSoup4`, `rich`, `tqdm`.
* **Database**: `SQLite3` (`major_cineplex.db`).
* **Dashboard**: Next.js 16 (App Router), `better-sqlite3`, Vanilla CSS.

---

## Setup & Installation

### 1. Scraper Setup
1. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install playwright beautifulsoup4 tqdm rich
   playwright install chromium
   ```

### 2. Dashboard Setup
1. Install Node modules:
   ```bash
   cd dashboard
   npm install
   ```

---

## How to Run

### 1. Run the Scraper (Daily)
To run a fresh crawl of all 193 cinemas, active showtimes, and seat maps:
```bash
source venv/bin/activate
python scraper.py
```
This will automatically generate a timestamped CSV report under the `reports/` folder and populate `major_cineplex.db`.

### 2. Export CSV Manually
To extract the complete historical database content into a new CSV report at any time:
```bash
source venv/bin/activate
python scraper.py --export
```

### 3. Start the Web Dashboard
To visualize live stats, top performing showtimes, and apply cinema/movie filters:
```bash
cd dashboard
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Documentation

* [Implementation Plan](docs/implementation_plan.md) — Detailed engineering architecture and technical decisions.
