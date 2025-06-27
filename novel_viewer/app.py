import sqlite3
from flask import Flask, render_template, g, abort
from functools import wraps

app = Flask(__name__)
DATABASE = 'NOVEL_SCHEMA_DATA.db'

def get_db():
    """Get or create database connection."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Close the database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def handle_db_errors(f):
    """Decorator to handle database errors and None results."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if result is None:
                abort(404, description="Requested resource not found")
            return result
        except sqlite3.Error as e:
            app.logger.error(f"Database error: {str(e)}")
            abort(500, description="Database operation failed")
    return wrapper

@app.route('/')
@handle_db_errors
def index():
    """Show all novels."""
    db = get_db()
    novels = db.execute('''
        SELECT id, title, description, cover_image_url, 
               status, progress, total_chapters 
        FROM novels 
        ORDER BY title
    ''').fetchall()
    return render_template('index.html', novels=novels)

@app.route('/novel/<int:novel_id>')
@handle_db_errors
def novel_detail(novel_id):
    """Show details for a specific novel."""
    db = get_db()
    
    # Get novel with explicit check for None
    novel = db.execute('SELECT * FROM novels WHERE id = ?', (novel_id,)).fetchone()
    if novel is None:
        abort(404, description=f"Novel with ID {novel_id} not found")
    
    # Get chapters - fetchall() returns empty list if no results
    chapters = db.execute('''
        SELECT id, chapter_number, title 
        FROM chapters 
        WHERE novel_id = ? 
        ORDER BY chapter_number
    ''', (novel_id,)).fetchall()
    
    # Get genres - fetchall() returns empty list if no results
    genres = db.execute('''
        SELECT g.name 
        FROM genres g
        JOIN novel_genres ng ON g.id = ng.genre_id
        WHERE ng.novel_id = ?
    ''', (novel_id,)).fetchall()
    
    return render_template(
        'novel_detail.html', 
        novel=dict(novel),  # Convert Row to dict to ensure safe access
        chapters=chapters, 
        genres=genres
    )

@app.route('/chapter/<int:chapter_id>')
@handle_db_errors
def chapter_view(chapter_id):
    """Show a specific chapter."""
    db = get_db()
    
    # Get chapter with explicit check for None
    chapter = db.execute('SELECT * FROM chapters WHERE id = ?', (chapter_id,)).fetchone()
    if chapter is None:
        abort(404, description=f"Chapter with ID {chapter_id} not found")
    
    # Get novel info with explicit check for None
    novel = db.execute('SELECT id, title FROM novels WHERE id = ?', (chapter['novel_id'],)).fetchone()
    if novel is None:
        abort(404, description=f"Associated novel not found for chapter {chapter_id}")
    
    return render_template(
        'chapter.html', 
        chapter=dict(chapter),  # Convert Row to dict to ensure safe access
        novel=dict(novel)       # Convert Row to dict to ensure safe access
    )

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html', error=error.description), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html', error=error.description), 500

if __name__ == '__main__':
    app.run(debug=True)