import Database from 'better-sqlite3';
import path from 'path';

export const dynamic = 'force-dynamic';

function getDbData(selectedCinema, selectedMovie, showAll) {
  try {
    const dbPath = path.resolve(process.cwd(), '../major_cineplex.db');
    const db = new Database(dbPath, { readonly: true });
    
    // 1. Get all unique cinemas for dropdown list
    const allCinemas = db.prepare("SELECT DISTINCT name FROM cinemas ORDER BY name ASC").all();
    
    // 2. Get all unique movies for dropdown list
    const allMovies = db.prepare("SELECT DISTINCT title FROM movies ORDER BY title ASC").all();
    
    // 3. Build dynamic filter clauses
    let filterClauses = [];
    let queryParams = [];
    
    if (selectedCinema) {
      filterClauses.push("c.name = ?");
      queryParams.push(selectedCinema);
    }
    
    if (selectedMovie) {
      filterClauses.push("m.title = ?");
      queryParams.push(selectedMovie);
    }
    
    const filterSql = filterClauses.length > 0 
      ? "AND " + filterClauses.join(" AND ") 
      : "";
      
    // 4. Calculate total count of matching showtimes
    const countQuery = `
      SELECT COUNT(DISTINCT s.id) as count
      FROM seat_occupancy so
      JOIN showtimes s ON so.showtime_id = s.id
      JOIN cinemas c ON s.cinema_id = c.id
      JOIN movies m ON s.movie_id = m.id
      WHERE so.id IN (
        SELECT MAX(id) FROM seat_occupancy GROUP BY showtime_id
      )
      ${filterSql}
    `;
    const totalCountResult = db.prepare(countQuery).get(...queryParams);
    const totalCount = totalCountResult ? totalCountResult.count : 0;
    
    // 5. Get aggregated stats with filter applied
    const statsQuery = `
      SELECT 
        COUNT(DISTINCT s.id) as total_showtimes,
        SUM(so.total_seats) as overall_capacity,
        SUM(so.sold_seats) as overall_sold,
        COUNT(DISTINCT c.id) as total_cinemas
      FROM seat_occupancy so
      JOIN showtimes s ON so.showtime_id = s.id
      JOIN cinemas c ON s.cinema_id = c.id
      JOIN movies m ON s.movie_id = m.id
      WHERE so.id IN (
        SELECT MAX(id) FROM seat_occupancy GROUP BY showtime_id
      )
      ${filterSql}
    `;
    const stats = db.prepare(statsQuery).get(...queryParams) || { total_showtimes: 0, overall_capacity: 0, overall_sold: 0, total_cinemas: 0 };
    
    // 6. Get showtimes list with dynamic limit
    const limit = showAll ? 10000 : 20;
    const listQuery = `
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
      WHERE so.id IN (
        SELECT MAX(id) FROM seat_occupancy GROUP BY showtime_id
      )
      ${filterSql}
      ORDER BY so.sold_seats DESC
      LIMIT ${limit}
    `;
    const rows = db.prepare(listQuery).all(...queryParams);
    
    db.close();
    return { stats, rows, allCinemas, allMovies, totalCount, error: null };
  } catch (error) {
    console.error("Database error:", error);
    return { 
      stats: { total_showtimes: 0, overall_capacity: 0, overall_sold: 0, total_cinemas: 0 }, 
      rows: [], 
      allCinemas: [],
      allMovies: [],
      totalCount: 0,
      error: error.message 
    };
  }
}

export default async function Home({ searchParams }) {
  const params = await searchParams;
  const cinemaFilter = params.cinema || '';
  const movieFilter = params.movie || '';
  const showAll = params.showAll === 'true';
  
  const { stats, rows, allCinemas, allMovies, totalCount, error } = getDbData(cinemaFilter, movieFilter, showAll);
  
  const occupancyRate = stats.overall_capacity > 0 
    ? ((stats.overall_sold / stats.overall_capacity) * 100).toFixed(1) 
    : 0;

  return (
    <main className="container">
      <div className="header">
        <div>
          <h1>Major Cineplex Pulse</h1>
          <p>Real-time seat booking intelligence</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ margin: 0, color: 'var(--success)' }}>● Live Data</p>
          <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>SQLite Connected</p>
        </div>
      </div>
      
      {error && (
        <div style={{ background: 'rgba(255, 51, 102, 0.1)', border: '1px solid var(--accent-color)', padding: '1rem', borderRadius: '8px', marginBottom: '2rem' }}>
          <strong>Error reading database:</strong> {error}
          <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem' }}>Have you run the scraper yet? `python scraper.py`</p>
        </div>
      )}

      {/* Dynamic Filter Bar */}
      <form method="GET" action="/" className="filter-bar">
        <div className="filter-group">
          <label htmlFor="cinema">Cinema</label>
          <select name="cinema" id="cinema" defaultValue={cinemaFilter}>
            <option value="">All Cinemas</option>
            {allCinemas.map((c, idx) => (
              <option key={idx} value={c.name}>{c.name}</option>
            ))}
          </select>
        </div>
        
        <div className="filter-group">
          <label htmlFor="movie">Movie</label>
          <select name="movie" id="movie" defaultValue={movieFilter}>
            <option value="">All Movies</option>
            {allMovies.map((m, idx) => (
              <option key={idx} value={m.title}>{m.title}</option>
            ))}
          </select>
        </div>
        
        <button type="submit" className="btn-filter">Apply Filters</button>
        {(cinemaFilter || movieFilter) && (
          <a href="/" className="btn-clear">Clear Filters</a>
        )}
      </form>

      <div className="grid">
        <div className="card">
          <h3>Seats Sold</h3>
          <div className="value">{stats.overall_sold?.toLocaleString() || 0}</div>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>across selected filter</p>
        </div>
        
        <div className="card">
          <h3>Occupancy Rate</h3>
          <div className="value">{occupancyRate}%</div>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Capacity: {stats.overall_capacity?.toLocaleString() || 0}</p>
        </div>
        
        <div className="card">
          <h3>Tracked Showtimes</h3>
          <div className="value">{stats.total_showtimes?.toLocaleString() || 0}</div>
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.9rem' }}>in {stats.total_cinemas} cinemas</p>
        </div>
      </div>

      <div className="table-container">
        <h2 className="table-header-title">
          {showAll ? `All Matching Showtimes (${totalCount})` : `Top Performing Showtimes (Showing ${rows.length} of ${totalCount})`}
        </h2>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Movie</th>
                <th>Cinema</th>
                <th>Showtime</th>
                <th>Occupancy</th>
                <th>Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                    No showtimes matched your filter query.
                  </td>
                </tr>
              ) : (
                rows.map((row, idx) => {
                  const percent = row.total_seats > 0 ? (row.sold_seats / row.total_seats) * 100 : 0;
                  return (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{row.movie}</td>
                      <td>{row.cinema}</td>
                      <td>{row.show_date} <span style={{ color: 'var(--accent-color)' }}>{row.show_time}</span></td>
                      <td style={{ minWidth: '150px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                          <span>{row.sold_seats} / {row.total_seats}</span>
                          <span>{percent.toFixed(0)}%</span>
                        </div>
                        <div className="occupancy-bar">
                          <div className="occupancy-fill" style={{ width: `${percent}%` }}></div>
                        </div>
                      </td>
                      <td style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                        {new Date(row.scraped_at).toLocaleString()}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
        
        {/* Table Footer with dynamic pagination buttons */}
        {totalCount > 20 && (
          <div className="table-footer">
            {showAll ? (
              <a 
                href={`/?cinema=${encodeURIComponent(cinemaFilter)}&movie=${encodeURIComponent(movieFilter)}`} 
                className="btn-show-less"
              >
                Show Less (Show Top 20)
              </a>
            ) : (
              <a 
                href={`/?cinema=${encodeURIComponent(cinemaFilter)}&movie=${encodeURIComponent(movieFilter)}&showAll=true`} 
                className="btn-show-all"
              >
                Show All ({totalCount} showtimes)
              </a>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
