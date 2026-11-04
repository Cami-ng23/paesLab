import json, os, re, hmac, random, datetime as dt
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
import engine, db

B = Path(__file__).parent
rd = lambda f: json.loads((B / 'content' / f).read_text(encoding='utf-8'))
CFG, UNITS, LESSONS = rd('config.json'), rd('units.json'), rd('lessons.json')
UD = {u['id']: u for u in UNITS}
LABEL = {'sin_estudiar': '🪑 En la banca', 'en_aprendizaje': '🔥 Calentando', 'aprobada_dx': '✅ Titular (por diagnóstico)',
         'aprobada': '✅ Titular', 'dominada': '👑 Capitán (dominada)', 'refuerzo': '🟨 Tarjeta amarilla: reforzar'}
OK = ('aprobada_dx', 'aprobada', 'dominada')
MODES = {'practica': 'Entrenamiento (con pistas)', 'repaso': 'Repaso (sin pistas)', 'diagnostico': 'Diagnóstico'}
PREMIOS = [(1.0, '🏆', 'Balón de Oro', 'Todas correctas sin ayuda'), (0.8, '🥇', 'Bota de Oro', '80% o más sin ayuda'),
           (0.6, '🥈', 'Medalla de plata', '60% o más sin ayuda'), (0.0, '⚽', 'Sigue entrenando', 'Cada error corregido te acerca')]
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'paeslab-local')
app.config.update(SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=bool(os.environ.get('RENDER')))
INVITE = os.environ.get('INVITE_CODE')  # opcional: si existe, hace falta para crear cuenta
db.init()

today = lambda: dt.date.today().isoformat()
me = lambda: session['uid']

@app.before_request
def gate():
    if not session.get('uid') and request.endpoint not in ('login', 'registro', 'static'): return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    err = None
    if request.method == 'POST':
        n, p = request.form.get('u', '').strip().lower(), request.form.get('p', '')
        if INVITE and not hmac.compare_digest(request.form.get('inv', ''), INVITE): err = 'Código de invitación incorrecto.'
        elif not re.fullmatch(r'[a-z0-9_]{3,20}', n): err = 'Usuario: 3 a 20 letras, números o _ (sin espacios).'
        elif len(p) < 8: err = 'La clave debe tener al menos 8 caracteres.'
        elif p != request.form.get('p2', ''): err = 'Las claves no coinciden.'
        else:
            try: db.run('insert into usuarios(username,pw_hash,created) values(?,?,?)', (n, generate_password_hash(p), today()))
            except Exception: err = 'Ese nombre de usuario ya existe.'
            else:
                session.clear(); session.update(uid=db.run('select id from usuarios where username=?', (n,), 'one')['id'], name=n)
                return redirect(url_for('index'))
    return render_template('registro.html', err=err, invite=bool(INVITE))

@app.route('/login', methods=['GET', 'POST'])
def login():
    bad = False
    if request.method == 'POST':
        row = db.run('select * from usuarios where username=?', (request.form.get('u', '').strip().lower(),), 'one')
        if row and check_password_hash(row['pw_hash'], request.form.get('p', '')):
            session.clear(); session.update(uid=row['id'], name=row['username']); return redirect(url_for('index'))
        bad = True
    return render_template('login.html', bad=bad)

@app.route('/salir', methods=['POST'])
def salir():
    session.clear(); return redirect(url_for('login'))

def states(U): return {r['unit']: dict(r) for r in db.run('select * from estado where user_id=?', (U,), 'all')}
def set_state(U, uid, status, **kw):
    cur = db.run('select * from estado where user_id=? and unit=?', (U, uid), 'one')
    d = dict(cur) if cur else dict(reviews=0, approved_at=None, next_review=None)
    d.update(status=status, **kw)
    db.run('insert into estado(user_id,unit,status,approved_at,reviews,next_review) values(?,?,?,?,?,?) on conflict(user_id,unit) do update set '
           'status=excluded.status, approved_at=excluded.approved_at, reviews=excluded.reviews, next_review=excluded.next_review',
           (U, uid, d['status'], d['approved_at'], d['reviews'], d['next_review']))
def temporada(st):
    out = {}
    for r in ('M1', 'M2'):
        us = [u for u in UNITS if u['route'] == r]; n = sum(st.get(u['id'], {}).get('status') in OK for u in us)
        out[r] = dict(done=n, total=len(us), pct=round(100 * n / len(us)), completa=n == len(us))
    return out
def premio(score, total):
    f = score / total
    return next(dict(icono=i, nombre=n, texto=t, nivel=k) for k, (m, i, n, t) in enumerate(PREMIOS) if f >= m)
def racha(U):
    ds = {r['ts'] for r in db.run('select ts from sesiones where user_id=?', (U,), 'all')}
    d, n = dt.date.today(), 0
    if d.isoformat() not in ds: d -= dt.timedelta(days=1)
    while d.isoformat() in ds: n += 1; d -= dt.timedelta(days=1)
    return n
@app.context_processor
def ctx(): return dict(LABEL=LABEL, MODES=MODES, OK=OK, TPL=engine.TEMPLATES, LESSONS=LESSONS)

@app.route('/')
def index():
    st = states(me()); temp = temporada(st)
    due = [u for u in UNITS if st.get(u['id'], {}).get('status') in ('aprobada_dx', 'aprobada') and (st[u['id']]['next_review'] or '9') <= today()]
    frase = random.choice(['Se gana en los entrenamientos que nadie ve.', 'Un problema bien resuelto vale más que diez copiados.', 'Primero entiendes, después aceleras.',
                           'La constancia le gana al talento que no entrena.', 'Cada error corregido es un pase que ya no pierdes.'])
    return render_template('index.html', units=UNITS, st=st, temp=temp, due=due, racha=racha(me()), frase=frase)

@app.route('/trofeos')
def trofeos():
    U = me(); temp = temporada(states(U)); cnt = [0] * len(PREMIOS)
    for r in db.run('select score,total from sesiones where user_id=?', (U,), 'all'): cnt[premio(r['score'], r['total'])['nivel']] += 1
    return render_template('trofeos.html', temp=temp, cnt=cnt, premios=PREMIOS, racha=racha(U))

@app.route('/unit/<uid>')
def unit(uid):
    U, u = me(), UD.get(uid) or abort(404)
    sess = db.run('select * from sesiones where user_id=? and unit=? order by id desc limit 8', (U, uid), 'all')
    a = db.run('select count(*) as n, sum(case when correct=1 and hints=0 and gaveup=0 then 1 else 0 end) as ind, '
               'sum(case when correct=1 and hints>0 then 1 else 0 end) as aid from intentos where user_id=? and unit=?', (U, uid), 'one')
    stt = states(U); falta = [p for p in u['prereqs'] if stt.get(p, {}).get('status') not in OK]
    return render_template('unit.html', u=u, st=stt.get(uid, {}), sess=sess, a=a, falta=falta, names={x['id']: x['name'] for x in UNITS})

@app.route('/teoria/<uid>')
def teoria(uid):
    u = UD.get(uid) or abort(404)
    return render_template('teoria.html', u=u, L=LESSONS.get(uid))

@app.route('/start/<uid>/<mode>', methods=['POST'])
def start(uid, mode):
    if uid not in engine.TEMPLATES or mode not in MODES: abort(404)
    T = engine.TEMPLATES[uid]; n = CFG['n_' + mode]; r = random.SystemRandom()
    items = [[r.randrange(len(T)), r.randrange(10**9)] for _ in range(n)]
    session['quiz'] = dict(uid=uid, mode=mode, items=items, pos=0, res=[], hints=0, tries=0, msg=None, fb=None)
    return redirect(url_for('q'))

def prob(z): return engine.build(z['uid'], *z['items'][z['pos']])
def need_quiz(): return None if 'quiz' in session else redirect(url_for('index'))

def advance(z, p, ok, gaveup, user):
    db.run('insert into intentos(user_id,unit,mode,ts,correct,hints,gaveup,skill) values(?,?,?,?,?,?,?,?)',
           (me(), z['uid'], z['mode'], today(), int(ok), z['hints'], int(gaveup), p['skill']))
    z['res'].append(dict(ok=ok, hints=z['hints'], gaveup=gaveup, user=user))
    z['fb'] = dict(ok=ok, gaveup=gaveup, user=user, text=p['text'], sol=p['sol'], hints=z['hints'])
    z['pos'] += 1; z['hints'] = z['tries'] = 0

@app.route('/q')
def q():
    z = session.get('quiz')
    if not z: return redirect(url_for('index'))
    if z.get('fb'):
        return render_template('feedback.html', z=z, fb=z['fb'], last=z['pos'] >= len(z['items']), u=UD[z['uid']], n=len(z['items']))
    if z['pos'] >= len(z['items']): return redirect(url_for('finish'))
    msg = z['msg']; z['msg'] = None; session.modified = True; p = prob(z)
    return render_template('question.html', z=z, p=p, u=UD[z['uid']], n=len(z['items']), msg=msg, hints=p['hints'][:z['hints']])

@app.route('/answer', methods=['POST'])
def answer():
    if (r := need_quiz()): return r
    z = session['quiz']
    if z.get('fb') or z['pos'] >= len(z['items']): return redirect(url_for('q'))
    p = prob(z); u = request.form.get('a', '')[:60]; stt, note = engine.check(p, u)
    if stt == 'format': z['msg'] = ('warn', note or 'No pude leer tu respuesta.')
    elif stt == 'ok': advance(z, p, True, False, u)
    elif z['mode'] == 'practica':  # entrenamiento: te detienes y eliges qué hacer; puedes reintentar
        z['tries'] += 1; z['msg'] = ('bad', note or 'Incorrecto. Revisa tu desarrollo en el cuaderno y elige qué hacer.')
    else: advance(z, p, False, False, u)  # repaso/diagnóstico: se explica al instante, sin repetir la pregunta
    session.modified = True; return redirect(url_for('q'))

@app.route('/next', methods=['POST'])
def next_q():
    if (r := need_quiz()): return r
    z = session['quiz']; z['fb'] = None; session.modified = True; return redirect(url_for('q'))

@app.route('/hint', methods=['POST'])
def hint():
    if (r := need_quiz()): return r
    z = session['quiz']
    if z['pos'] < len(z['items']) and not z.get('fb'): z['hints'] = min(z['hints'] + 1, len(prob(z)['hints']))
    session.modified = True; return redirect(url_for('q'))

@app.route('/giveup', methods=['POST'])
def giveup():
    if (r := need_quiz()): return r
    z = session['quiz']
    if z['mode'] == 'practica' and z['pos'] < len(z['items']) and not z.get('fb'): advance(z, prob(z), False, True, '')
    session.modified = True; return redirect(url_for('q'))

@app.route('/finish')
def finish():
    z = session.pop('quiz', None)
    if not z: return redirect(url_for('index'))
    U, uid, mode = me(), z['uid'], z['mode']; route = UD[uid]['route']; total = len(z['items'])
    score = sum(r['ok'] and r['hints'] == 0 and not r['gaveup'] for r in z['res'])
    passed = score / total >= CFG['pass_pct']; days = CFG['review_days']
    antes = temporada(states(U))[route]['completa']
    db.run('insert into sesiones(user_id,unit,mode,ts,score,total,passed) values(?,?,?,?,?,?,?)', (U, uid, mode, today(), score, total, int(passed)))
    cur = db.run('select * from estado where user_id=? and unit=?', (U, uid), 'one'); cur = dict(cur) if cur else dict(status='sin_estudiar', reviews=0)
    nxt = lambda k: (dt.date.today() + dt.timedelta(days=days[min(k, len(days) - 1)])).isoformat()
    ok_prev = cur['status'] in OK
    if mode == 'diagnostico':
        if passed: set_state(U, uid, 'aprobada_dx', approved_at=today(), reviews=0, next_review=nxt(0))
        else: set_state(U, uid, 'en_aprendizaje' if cur['status'] == 'sin_estudiar' else 'refuerzo')
    elif mode == 'repaso':
        if not ok_prev:
            if passed: set_state(U, uid, 'aprobada', approved_at=today(), reviews=0, next_review=nxt(0))
            else: set_state(U, uid, 'en_aprendizaje' if cur['status'] == 'sin_estudiar' else 'refuerzo')
        elif not passed: set_state(U, uid, 'refuerzo', reviews=0)
        elif cur['reviews'] + 1 >= len(days): set_state(U, uid, 'dominada', reviews=cur['reviews'] + 1, next_review=None)
        else: set_state(U, uid, cur['status'], reviews=cur['reviews'] + 1, next_review=nxt(cur['reviews'] + 1))
    elif cur['status'] == 'sin_estudiar': set_state(U, uid, 'en_aprendizaje')
    temp = temporada(states(U))[route]
    rows = [dict(p=engine.build(uid, ti, sd), r=r) for (ti, sd), r in zip(z['items'], z['res'])]
    return render_template('result.html', u=UD[uid], mode=mode, score=score, total=total, passed=passed, rows=rows, pr=premio(score, total),
                           temp=temp, route=route, campeon=temp['completa'] and not antes, nuevo_estado=states(U).get(uid, {}).get('status'))

if __name__ == '__main__':
    app.run(debug=os.environ.get('DEBUG') == '1')
