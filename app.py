# ...existing code...
from flask import Flask, g, request, redirect, url_for, render_template_string, abort
import sqlite3, os
from datetime import datetime

DB = os.path.join(os.path.dirname(__file__), 'boardgames.db')
SCHEMA = """
CREATE TABLE IF NOT EXISTS giochi (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  numero_giocatori_massimo INTEGER NOT NULL,
  durata_media INTEGER NOT NULL,
  categoria TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS partite (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  gioco_id INTEGER NOT NULL,
  data DATE NOT NULL,
  vincitore TEXT NOT NULL,
  punteggio_vincitore INTEGER NOT NULL,
  FOREIGN KEY (gioco_id) REFERENCES giochi (id)
);
"""

SAMPLE = """
INSERT INTO giochi (nome, numero_giocatori_massimo, durata_media, categoria) VALUES
 ('Catan',4,90,'Strategia'),('Dixit',6,30,'Party'),('Ticket to Ride',5,60,'Strategia');
INSERT INTO partite (gioco_id, data, vincitore, punteggio_vincitore) VALUES
 (1,'2023-10-15','Alice',10),(1,'2023-10-22','Bob',12),(2,'2023-11-05','Charlie',25),(3,'2023-11-10','Alice',8);
"""

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_=None):
    db = g.pop('db', None)
    if db: db.close()


def init_db():
    if not os.path.exists(DB):
        conn = sqlite3.connect(DB)
        conn.executescript(SCHEMA + SAMPLE)
        conn.commit()
        conn.close()


@app.route('/')
def index():
    return redirect(url_for('list_games'))


@app.route('/games')
def list_games():
    db = get_db()
    games = db.execute("SELECT * FROM giochi ORDER BY nome").fetchall()
    return render_template_string("""
    <h1>Giochi</h1>
    <a href="{{ url_for('new_game') }}">Nuovo gioco</a>
    <ul>{% for g in games %}
      <li>{{g['nome']}} — max {{g['numero_giocatori_massimo']}}, {{g['durata_media']}}min, {{g['categoria']}}
      [<a href="{{ url_for('list_matches', game_id=g['id']) }}">partite</a>]
      [<a href="{{ url_for('new_match', game_id=g['id']) }}">registra</a>]</li>
    {% else %}<li>Nessun gioco.</li>{% endfor %}</ul>
    """, games=games)


@app.route('/games/new', methods=('GET', 'POST'))
def new_game():
    if request.method == 'POST':
        n = request.form.get('nome','').strip()
        try:
            num = int(request.form.get('numero_giocatori_massimo',0))
            dur = int(request.form.get('durata_media',0))
        except:
            return "Numero o durata non validi", 400
        cat = request.form.get('categoria','').strip()
        if not (n and num>0 and dur>0 and cat): return "Dati mancanti", 400
        db = get_db()
        db.execute("INSERT INTO giochi (nome,numero_giocatori_massimo,durata_media,categoria) VALUES (?,?,?,?)",
                   (n,num,dur,cat))
        db.commit()
        return redirect(url_for('list_games'))
    return render_template_string("""
    <h1>Nuovo Gioco</h1>
    <form method="post">
    Nome: <input name="nome"><br>
    Numero max: <input name="numero_giocatori_massimo" type="number" min="1"><br>
    Durata min: <input name="durata_media" type="number" min="1"><br>
    Categoria: <input name="categoria"><br>
    <button type="submit">Crea</button>
    </form><a href="{{ url_for('list_games') }}">Indietro</a>
    """)


@app.route('/games/<int:game_id>/matches')
def list_matches(game_id):
    db = get_db()
    game = db.execute("SELECT * FROM giochi WHERE id=?",(game_id,)).fetchone()
    if not game: abort(404)
    matches = db.execute("SELECT * FROM partite WHERE gioco_id=? ORDER BY data DESC",(game_id,)).fetchall()
    return render_template_string("""
    <h1>Partite di {{game['nome']}}</h1>
    <a href="{{ url_for('new_match', game_id=game['id']) }}">Registra</a> |
    <a href="{{ url_for('list_games') }}">Giochi</a>
    <ul>{% for m in matches %}<li>{{m['data']}} — {{m['vincitore']}} ({{m['punteggio_vincitore']}})</li>{% else %}<li>Nessuna partita.</li>{% endfor %}</ul>
    """, game=game, matches=matches)


@app.route('/games/<int:game_id>/matches/new', methods=('GET','POST'))
def new_match(game_id):
    db = get_db()
    game = db.execute("SELECT * FROM giochi WHERE id=?",(game_id,)).fetchone()
    if not game: abort(404)
    if request.method == 'POST':
        d = request.form.get('data','').strip()
        v = request.form.get('vincitore','').strip()
        try:
            datetime.strptime(d,'%Y-%m-%d')
            p = int(request.form.get('punteggio_vincitore',0))
        except:
            return "Data o punteggio non validi", 400
        if not v: return "Vincitore richiesto", 400
        db.execute("INSERT INTO partite (gioco_id,data,vincitore,punteggio_vincitore) VALUES (?,?,?,?)",
                   (game_id,d,v,p))
        db.commit()
        return redirect(url_for('list_matches', game_id=game_id))
    today = datetime.today().strftime('%Y-%m-%d')
    return render_template_string("""
    <h1>Nuova partita per {{game['nome']}}</h1>
    <form method="post">
    Data: <input name="data" type="date" value="{{today}}"><br>
    Vincitore: <input name="vincitore"><br>
    Punteggio: <input name="punteggio_vincitore" type="number" min="0"><br>
    <button type="submit">Registra</button>
    </form><a href="{{ url_for('list_matches', game_id=game['id']) }}">Indietro</a>
    """, game=game, today=today)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
# ...existing code...