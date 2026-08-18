# Major Cineplex Seat Dashboard

This app collects current Major Cineplex showtimes and seat availability. It saves the data in a local SQLite database and displays the latest data in a web dashboard.

The app has two parts:

1. **Scraper**: Collects cinema, movie, showtime, and seat data from the Major Cineplex website.
2. **Dashboard**: Shows the collected data in your web browser. You can filter the results by cinema or movie.

You need an internet connection when you run the scraper.

## Requirements

Install these tools before you start:

- [Git](https://git-scm.com/downloads) - downloads the project from GitHub.
- [Python 3.9 or newer](https://www.python.org/downloads/) - runs the scraper.
- [Node.js 20.9 or newer](https://nodejs.org/en/download) - runs the web dashboard. The Node.js installer also installs `npm`.

You can check whether the tools are installed by opening Terminal (macOS/Linux) or PowerShell (Windows) and running:

```bash
git --version
python3 --version
node --version
npm --version
```

On Windows, use `python --version` if `python3 --version` does not work.

## Installation

Follow these steps in order.

### 1. Download the project

Open Terminal or PowerShell and run:

```bash
git clone https://github.com/zwka/major-cineplex.git
cd major-cineplex
```

The `cd major-cineplex` command moves into the project folder. Run the remaining commands from this folder unless a step says otherwise.

### 2. Create a Python environment

A virtual environment keeps this project's Python packages separate from other Python projects on your computer.

On macOS or Linux, run:

```bash
python3 -m venv venv
source venv/bin/activate
```

On Windows PowerShell, run:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

When the environment is active, your command prompt usually starts with `(venv)`.

### 3. Install scraper packages

With the virtual environment active, run:

```bash
python -m pip install --upgrade pip
python -m pip install playwright beautifulsoup4 tqdm rich
python -m playwright install chromium
```

The last command downloads the Chromium browser that the scraper uses.

### 4. Install dashboard packages

Run:

```bash
cd dashboard
npm install
cd ..
```

The dashboard packages are installed in `dashboard/node_modules`.

## Run the app

The scraper must run once before you start the dashboard. This creates the database that the dashboard reads.

### 1. Collect the latest data

Make sure you are in the main project folder and that the Python environment is active. Then run:

```bash
python scraper.py
```

The scraper checks the available cinemas and the current day's showtimes. It then checks seat availability and saves the results.

When the command finishes, you should see these generated files:

- `major_cineplex.db` - the local database used by the dashboard.
- `reports/major_cineplex_<timestamp>.csv` - a CSV report from this run.

The scraper can take some time because it checks many cinemas and showtimes. Leave the command running until the summary says the run is complete.

### 2. Start the dashboard

Open a second Terminal or PowerShell window. Move to the dashboard folder inside the cloned project:

```bash
cd major-cineplex/dashboard
npm run dev
```

Keep this command running while you use the dashboard. Open [http://localhost:3000](http://localhost:3000) in your browser.

The dashboard shows seat totals, occupancy rates, and showtimes. Use the cinema and movie lists to filter the results.

## Update the data

The dashboard displays the data stored in `major_cineplex.db`. To collect a newer snapshot:

1. Open another Terminal or PowerShell window.
2. Move to the main project folder.
3. Activate the Python environment.
4. Run the scraper.
5. Refresh the dashboard in your browser.

On macOS or Linux:

```bash
cd major-cineplex
source venv/bin/activate
python scraper.py
```

On Windows PowerShell:

```powershell
cd major-cineplex
.\venv\Scripts\Activate.ps1
python scraper.py
```

You can keep the dashboard running while the scraper updates the database.

## Export the database to CSV

To create a CSV file containing all saved seat records, run this from the main project folder with the Python environment active:

```bash
python scraper.py --export
```

The new file is saved in the `reports/` folder.

## Troubleshooting

### The dashboard says it cannot read the database

Run `python scraper.py` from the main project folder first. The scraper must finish successfully before `major_cineplex.db` contains data.

### Playwright says that Chromium is missing

Activate the Python environment and run:

```bash
python -m playwright install chromium
```

### `python3`, `node`, or `npm` is not recognised

Install the missing tool from the links in the [Requirements](#requirements) section, then close and reopen your Terminal or PowerShell window.

### Port 3000 is already in use

Start the dashboard on another port:

```bash
npm run dev -- --port 3001
```

Then open [http://localhost:3001](http://localhost:3001).

## Project files

```text
scraper.py                 Collects data and creates CSV reports
major_cineplex.db          Generated SQLite database
reports/                   Generated CSV reports
dashboard/                 Next.js web dashboard
docs/implementation_plan.md  Technical implementation notes
```

## Development commands

Run these commands from the `dashboard` folder:

```bash
npm run dev       # Start the dashboard in development mode
npm run build     # Create a production build
npm run start     # Start the production build
```
