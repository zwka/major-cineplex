import asyncio
import sqlite3
import csv
import os
import re
import json
import html as html_lib
from datetime import datetime
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from bs4 import BeautifulSoup

console = Console()
DB_FILE = 'major_cineplex.db'
CONCURRENCY_LIMIT = 10 # Number of parallel requests

def setup_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS cinemas (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            url TEXT
        );

        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS showtimes (
            id INTEGER PRIMARY KEY,
            cinema_id INTEGER,
            movie_id INTEGER,
            show_date TEXT,
            show_time TEXT,
            url TEXT UNIQUE,
            FOREIGN KEY(cinema_id) REFERENCES cinemas(id),
            FOREIGN KEY(movie_id) REFERENCES movies(id)
        );

        CREATE TABLE IF NOT EXISTS seat_occupancy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            showtime_id INTEGER,
            total_seats INTEGER,
            sold_seats INTEGER,
            available_seats INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(showtime_id) REFERENCES showtimes(id)
        );
    """)
    conn.commit()
    return conn

def save_data_to_db(conn, cinemas_dict, scraped_data):
    """
    Saves all cinemas and scraped showtime/seat data to SQLite in a safe transaction.
    """
    cursor = conn.cursor()
    
    # 1. Insert/update all cinemas
    for cid, name in cinemas_dict.items():
        cursor.execute("INSERT OR REPLACE INTO cinemas (id, name, url) VALUES (?, ?, ?)", 
                       (cid, name, f"https://www.majorcineplex.com/booking2/search_showtime/cinema={cid}"))
        
    # 2. Insert movies, showtimes, and seat occupancies
    for item in scraped_data:
        movie_title = item['movie_title']
        showtime_id = int(item['showtime_id'])
        cinema_id = item['cinema_id']
        show_date = item['show_date']
        show_time = item['show_time']
        total = item['total_seats']
        sold = item['sold_seats']
        avail = item['available_seats']
        
        # Get or create movie
        cursor.execute("INSERT OR IGNORE INTO movies (title) VALUES (?)", (movie_title,))
        cursor.execute("SELECT id FROM movies WHERE title = ?", (movie_title,))
        movie_id = cursor.fetchone()[0]
        
        # Get or create showtime
        url = f"https://www.majorcineplex.com/booking2/get_seat/{showtime_id}"
        cursor.execute("""
            INSERT OR REPLACE INTO showtimes (id, cinema_id, movie_id, show_date, show_time, url) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (showtime_id, cinema_id, movie_id, show_date, show_time, url))
        
        # Insert seat occupancy log
        cursor.execute("""
            INSERT INTO seat_occupancy (showtime_id, total_seats, sold_seats, available_seats) 
            VALUES (?, ?, ?, ?)
        """, (showtime_id, total, sold, avail))
        
    conn.commit()

def export_csv():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    query = """
    SELECT 
        c.name AS cinema,
        m.title AS movie,
        s.show_date,
        s.show_time,
        so.total_seats,
        so.sold_seats,
        so.available_seats,
        so.scraped_at
    FROM seat_occupancy so
    JOIN showtimes s ON so.showtime_id = s.id
    JOIN cinemas c ON s.cinema_id = c.id
    JOIN movies m ON s.movie_id = m.id
    ORDER BY so.scraped_at DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    headers = [description[0] for description in cursor.description]
    
    os.makedirs('reports', exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"reports/major_cineplex_{timestamp}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
        
    console.print(f"[bold green]✓[/bold green] Exported {len(rows)} records to [cyan]{filename}[/cyan]")
    conn.close()

async def scrape_showtime_seats(request_context, showtime_id, sem):
    url = f"https://www.majorcineplex.com/booking2/get_seat/{showtime_id}"
    async with sem:
        try:
            response = await request_context.get(url)
            html_content = await response.text()
            
            match = re.search(r"var seat_data_string = '(.*?)';", html_content)
            if not match:
                return None, None, None
                
            data = json.loads(html_lib.unescape(match.group(1)))
            seats = data.get('result', {}).get('seats', [])
            if not seats:
                return None, None, None
                
            total_seats = 0
            sold_seats = 0
            available_seats = 0
            
            for row in seats:
                for col in row.get('Columns', []):
                    if isinstance(col, dict) and 'Id' in col:
                        total_seats += 1
                        status = str(col.get('Status'))
                        if status in ('0', 'Reserved'):
                            available_seats += 1
                        else:
                            sold_seats += 1
                    elif isinstance(col, list):
                        for item in col:
                            if isinstance(item, dict) and 'Id' in item:
                                total_seats += 1
                                status = str(item.get('Status'))
                                if status in ('0', 'Reserved'):
                                    available_seats += 1
                                else:
                                    sold_seats += 1
                                    
            return total_seats, sold_seats, available_seats
        except Exception as e:
            return None, None, None

async def scrape_cinema_showtimes(request_context, target_id, show_date, sem, showtime_list):
    async with sem:
        try:
            response = await request_context.post(
                "https://www.majorcineplex.com/booking2/get_showtime/",
                form={
                    'movie_text': '',
                    'cinema_text': str(target_id),
                    'flag_special_cinema': 'normal',
                    'flag_type_showtime': 'one_cinema',
                    'date_link': show_date
                }
            )
            showtime_html = await response.text()
            soup_showtime = BeautifulSoup(showtime_html, 'html.parser')
            
            movies = soup_showtime.find_all(class_='bscbb-movie')
            for movie in movies:
                title_div = movie.find(class_='bscbbm-cover-title')
                movie_title = title_div.text.strip() if title_div else None
                if not movie_title:
                    continue
                
                links = movie.find_all('a', attrs={'data-showtime': True})
                for link in links:
                    showtime_list.append({
                        'cinema_id': target_id,
                        'movie_title': movie_title,
                        'show_time': link.text.strip(),
                        'showtime_id': link['data-showtime'],
                        'show_date': show_date
                    })
        except Exception:
            pass

async def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        export_csv()
        return

    conn = setup_db()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # 1. Set language session to English to ensure all returned text is in English
        console.print("[bold cyan]1. Setting site language session to English...[/bold cyan]")
        await context.request.get("https://www.majorcineplex.com/home/set_session/en")
        
        # 2. Fetch all available cinemas in English
        console.print("[bold cyan]2. Fetching all available cinemas (in English)...[/bold cyan]")
        response = await context.request.get("https://www.majorcineplex.com/cinema/")
        html_content = await response.text()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        fav_links = soup.find_all(class_='add_cinema_fav')
        cinemas = {}
        for link in fav_links:
            cid = link.get('data-cinema-id')
            if not cid:
                continue
            
            # Extract cinema name
            parent = link.parent
            text = ""
            for depth in range(5):
                if not parent:
                    break
                text = parent.text.strip()
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    break
                parent = parent.parent
            
            name = ""
            container = link.find_parent(class_='cinema_div_list') or link.find_parent(class_='bch-name') or link.find_parent('div')
            if container:
                cinema_a = container.find('a', href=lambda x: x and '/cinema/' in x)
                if cinema_a:
                    name = cinema_a.text.strip()
            
            if not name:
                name = text if text else f"Cinema {cid}"
                
            cinemas[int(cid)] = name
            
        console.print(f"Loaded [bold green]{len(cinemas)}[/bold green] unique cinemas in English.")
        
        # 3. Fetch all showtimes for all cinemas concurrently
        show_date = datetime.now().strftime("%Y-%m-%d")
        showtime_list = []
        sem = asyncio.Semaphore(CONCURRENCY_LIMIT)
        
        console.print(f"[bold cyan]3. Fetching all showtimes for {len(cinemas)} cinemas...[/bold cyan]")
        tasks = [
            scrape_cinema_showtimes(context.request, cid, show_date, sem, showtime_list)
            for cid in cinemas.keys()
        ]
        
        # Run showtime extraction with progress bar
        await tqdm.gather(*tasks, desc="Loading showtimes list", unit="cinema")
        
        console.print(f"Found [bold green]{len(showtime_list)}[/bold green] showtimes across all cinemas.")
        
        # 4. Scrape seat maps for all showtimes concurrently
        scraped_data = []
        success_count = 0
        skip_count = 0
        
        async def process_showtime_seat(item):
            nonlocal success_count, skip_count
            total, sold, avail = await scrape_showtime_seats(context.request, item['showtime_id'], sem)
            if total is not None:
                item['total_seats'] = total
                item['sold_seats'] = sold
                item['available_seats'] = avail
                scraped_data.append(item)
                success_count += 1
            else:
                skip_count += 1
                
        seat_tasks = [process_showtime_seat(item) for item in showtime_list]
        
        console.print(f"[bold cyan]4. Scraping seat maps for {len(showtime_list)} showtimes...[/bold cyan]")
        await tqdm.gather(*seat_tasks, desc="Scraping seat availability", unit="showtime")
        
        # 5. Save all collected data in a single SQL transaction
        console.print("[bold cyan]5. Saving all data to SQLite database...[/bold cyan]")
        save_data_to_db(conn, cinemas, scraped_data)
        
        await browser.close()
        
    conn.close()
    
    # Print Summary Report
    table = Table(title="Scrape Summary Report")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="magenta")
    table.add_row("Total Cinemas Scraped", str(len(cinemas)))
    table.add_row("Total Showtimes Found", str(len(showtime_list)))
    table.add_row("Successfully Scraped Seats", str(success_count))
    table.add_row("Skipped/Failed Seats", str(skip_count))
    
    console.print(Panel(table, title="Run Complete", expand=False))
    
    # Auto export at the end of scrape
    export_csv()

if __name__ == "__main__":
    asyncio.run(main())
