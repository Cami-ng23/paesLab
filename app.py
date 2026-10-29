import json, os, hmac, random, sqlite3, datetime as dt
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session
import engine

B = Path(__file__).parent
CFG = json.loads((B / 'content/config.json').read_text(encoding='utf-8'))
UNITS = json.loads((B / 'content/units.json').read_text(encoding='utf-8'))
UD = {u['id']: u for u in UNITS}
LABEL = {'sin_estudiar': '🪑 En la banca', 'en_aprendizaje': '🔥 Calentando', 'aprobada_dx': '✅ Titular (por diagnóstico)',
         'aprobada': '✅ Titular', 'dominada': '👑 Capitán (dominada)', 'refuerzo': '🟨 Tarjeta amarilla: reforzar'}
OK = ('aprobada_dx', 'aprobada', 'dominada')
MODES = {'diagnostico': 'Diagnóstico', 'practica': 'Entrenamiento (con pistas)', 'evaluacion': 'Final de dominio', 'repaso': 'Repaso'}
app = Flask(__name__); app.secret_key = os.environ.get('SECRET_KEY', 'paeslab-local')
PWD = os.environ.get('APP_PASSWORD')
DB = Path(os.environ.get('DATA_DIR', B)) / 'paeslab.db'

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c
with db() as c:
    c.executescript('''create table if not exists attempts(id integer primary key,unit text,mode text,ts text,correct int,hints int,gaveup int,skill text);
    create table if not exists state(unit text primary key,status text,approved_at text,reviews int default 0,next_review text);
    create table if not exists sessions(id integer primary key,unit text,mode text,ts text,score int,total int,passed int);''')

@app.before_request
def gate():
    if PWD and not session.get('auth') and request.endpoint not in ('login', 'static'): return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    bad = False
    if request.method == 'POST':
        if hmac.compare_digest(request.form.get('p', ''), PWD or ''): session['auth'] = 1; return redirect(url_for('index'))
        bad = True
    return render_template('login.html', bad=bad)

today = lambda: dt.date.today().isoformat()
def states():
    with db() as c: return {r['unit']: dict(r) for r in c.execute('select * from state')}
def set_state(c, uid, status, **kw):
    cur = c.execute('select * from state where unit=?', (uid,)).fetchone()
    d = dict(cur) if cur else dict(unit=uid, reviews=0, approved_at=None, next_review=None)
    d.update(status=status, **kw)
    c.execute('insert or replace into state values(:unit,:status,:approved_at,:reviews,:next_review)', d)
@app.context_processor
def ctx(): return dict(LABEL=LABEL, MODES=MODES, OK=OK, TPL=engine.TEMPLATES)

def racha():
    with db() as c: ds = {r[0] for r in c.execute('select ts from sessions')}
    d, n = dt.date.today(), 0
    if d.isoformat() not in ds: d -= dt.timedelta(days=1)
    while d.isoformat() in ds: n += 1; d -= dt.timedelta(days=1)
    return n

@app.route('/')
def index():
    st = states(); prog = {}
    for r in ('M1', 'M2'):
        us = [u for u in UNITS if u['route'] == r]
        prog[r] = round(100 * sum(st.get(u['id'], {}).get('status') in OK + ('dominada',) for u in us) / len(us))
    due = [u for u in UNITS if st.get(u['id'], {}).get('status') in ('aprobada_dx', 'aprobada') and (st[u['id']]['next_review'] or '9') <= today()]
    cnt = {r: (sum(st.get(u['id'], {}).get('status') in OK for u in UNITS if u['route'] == r), sum(u['route'] == r for u in UNITS)) for r in ('M1', 'M2')}
    frase = random.choice(['Se gana en los entrenamientos que nadie ve.', 'Un problema bien resuelto vale más que diez copiados.', 'Primero entiendes, después aceleras.', 'La constancia le gana al talento que no entrena.', 'Cada error corregido es un pase que ya no pierdes.'])
    return render_template('index.html', units=UNITS, st=st, prog=prog, due=due, cnt=cnt, racha=racha(), frase=frase)

@app.route('/unit/<uid>')
def unit(uid):
    u = UD[uid]
    with db() as c:
        sess = c.execute('select * from sessions where unit=? order by id desc limit 8', (uid,)).fetchall()
        a = c.execute('select count(*) n, sum(correct and hints=0 and not gaveup) ind, sum(correct and hints>0) aid from attempts where unit=?', (uid,)).fetchone()
    st = states().get(uid, {}); falta = [p for p in u['prereqs'] if states().get(p, {}).get('status') not in OK]
    return render_template('unit.html', u=u, st=st, sess=sess, a=a, falta=falta, names={x['id']: x['name'] for x in UNITS})

@app.route('/start/<uid>/<mode>', methods=['POST'])
def start(uid, mode):
    T = engine.TEMPLATES[uid]; n = CFG['n_' + mode]; r = random.SystemRandom()
    idx = list(range(len(T))); first = []
    if mode == 'evaluacion':  # garantiza 1 de Argumentar y 2 contextualizados si existen
        first += [i for i in idx if T[i]['skill'] == 'Argumentar'][:1] + [i for i in idx if T[i]['ctx']][:1] * 2
    items = [[i, r.randrange(10**9)] for i in first] + [[r.choice(idx), r.randrange(10**9)] for _ in range(n - len(first))]
    r.shuffle(items)
    session['quiz'] = dict(uid=uid, mode=mode, items=items, pos=0, res=[], hints=0, tries=0, msg=None)
    return redirect(url_for('q'))

def prob(z): return engine.build(z['uid'], *z['items'][z['pos']])
def advance(z, p, ok, gaveup, user):
    with db() as c:
        c.execute('insert into attempts(unit,mode,ts,correct,hints,gaveup,skill) values(?,?,?,?,?,?,?)', (z['uid'], z['mode'], today(), int(ok), z['hints'], int(gaveup), p['skill']))
    z['res'].append(dict(ok=ok, hints=z['hints'], gaveup=gaveup, user=user)); z['pos'] += 1; z['hints'] = z['tries'] = 0

@app.route('/q')
def q():
    z = session.get('quiz')
    if not z: return redirect(url_for('index'))
    if z['pos'] >= len(z['items']): return redirect(url_for('finish'))
    msg = z['msg']; z['msg'] = None; session.modified = True; p = prob(z)
    return render_template('question.html', z=z, p=p, u=UD[z['uid']], n=len(z['items']), msg=msg, hints=p['hints'][:z['hints']])

@app.route('/answer', methods=['POST'])
def answer():
    if 'quiz' not in session: return redirect(url_for('index'))
    z = session['quiz']; p = prob(z); u = request.form['a']; stt, note = engine.check(p, u)
    if stt == 'format': z['msg'] = ('warn', note)
    elif stt == 'ok': z['msg'] = ('ok', 'Correcto.' + (' (con ayuda: no cuenta como independiente)' if z['hints'] else '')) if z['mode'] == 'practica' else None; advance(z, p, True, False, u)
    elif z['mode'] == 'practica':
        z['tries'] += 1; z['msg'] = ('bad', note or 'Incorrecto. Revisa tu desarrollo; puedes pedir una pista o intentar de nuevo.')
    else: advance(z, p, False, False, u)
    session.modified = True; return redirect(url_for('q'))

@app.route('/hint', methods=['POST'])
def hint():
    if 'quiz' not in session: return redirect(url_for('index'))
    z = session['quiz']; z['hints'] = min(z['hints'] + 1, len(prob(z)['hints'])); session.modified = True; return redirect(url_for('q'))

@app.route('/giveup', methods=['POST'])
def giveup():
    if 'quiz' not in session: return redirect(url_for('index'))
    z = session['quiz']; p = prob(z); advance(z, p, False, True, ''); z['msg'] = ('info', 'Solución: ' + p['sol']); session.modified = True; return redirect(url_for('q'))

@app.route('/finish')
def finish():
    z = session.pop('quiz', None)
    if not z: return redirect(url_for('index'))
    uid, mode = z['uid'], z['mode']; total = len(z['items']); score = sum(r['ok'] and r['hints'] == 0 and not r['gaveup'] for r in z['res'])
    passed = score / total >= CFG['pass_pct']; days = CFG['review_days']
    with db() as c:
        c.execute('insert into sessions(unit,mode,ts,score,total,passed) values(?,?,?,?,?,?)', (uid, mode, today(), score, total, int(passed)))
        cur = c.execute('select * from state where unit=?', (uid,)).fetchone(); cur = dict(cur) if cur else dict(status='sin_estudiar', reviews=0)
        nxt = lambda k: (dt.date.today() + dt.timedelta(days=days[min(k, len(days) - 1)])).isoformat()
        if mode in ('diagnostico', 'evaluacion'):
            if passed: set_state(c, uid, 'aprobada_dx' if mode == 'diagnostico' else 'aprobada', approved_at=today(), reviews=0, next_review=nxt(0))
            else: set_state(c, uid, 'en_aprendizaje' if mode == 'diagnostico' and cur['status'] == 'sin_estudiar' else 'refuerzo')
        elif mode == 'repaso':
            if not passed: set_state(c, uid, 'refuerzo', reviews=0)
            elif cur['reviews'] + 1 >= len(days): set_state(c, uid, 'dominada', reviews=cur['reviews'] + 1, next_review=None)
            else: set_state(c, uid, cur['status'], reviews=cur['reviews'] + 1, next_review=nxt(cur['reviews'] + 1))
        elif cur['status'] == 'sin_estudiar': set_state(c, uid, 'en_aprendizaje')
    rows = []
    for (ti, sd), r in zip(z['items'], z['res']):
        p = engine.build(uid, ti, sd); rows.append(dict(p=p, r=r))
    return render_template('result.html', u=UD[uid], mode=mode, score=score, total=total, passed=passed, rows=rows)

if __name__ == '__main__':
    app.run(debug=os.environ.get('DEBUG') == '1')
