"""Motor matemático: plantillas parametrizadas + validación. Sin dependencias de Flask."""
import random, re
from sympy import symbols, simplify, expand
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application, convert_xor
TR = standard_transformations + (implicit_multiplication_application, convert_xor)
x, y = symbols('x y')
TEMPLATES = {}

def tpl(uid, skill='Resolver problemas', ctx=False):
    def d(f):
        TEMPLATES.setdefault(uid, []).append(dict(fn=f, skill=skill, ctx=ctx)); return f
    return d

def build(uid, i, seed):
    t = TEMPLATES[uid][i]; p = t['fn'](random.Random(seed)); p['skill'] = t['skill']; p['ctx'] = t['ctx']; return p

def _seguro(s):
    if len(s) > 60 or not re.fullmatch(r'[0-9a-zA-Zπ+\-−*/^().,;\s]*', s): raise ValueError('caracteres')
    if re.search(r'\*\*|\^[^+\-*/]*\^|\^\s*\(?-?\d{3,}|\d{9,}', s): raise ValueError('potencia')
    if any(re.sub(r'pi|sqrt|x|y|π', '', t) for t in re.findall(r'[a-zA-Zπ]+', s)): raise ValueError('nombre')
    return s

def _num(s):
    _seguro(s)
    s = s.strip().replace('$', '').replace('%', '').replace(' ', '').replace(',', '.').replace('−', '-')
    return float(parse_expr(s, transformations=TR, local_dict={}))

def _ex(s):
    _seguro(s)
    return parse_expr(s.replace('−', '-').replace('π', 'pi'), transformations=TR, local_dict={'x': x, 'y': y})

def check(p, u):
    """Devuelve (estado, nota). estado: ok | wrong | incomplete | format."""
    t = p['type']
    try:
        if t == 'num':
            return ('ok', '') if abs(_num(u) - p['ans']) <= p.get('tol', 1e-6) else ('wrong', '')
        if t == 'pair':
            parts = [q for q in re.split(r'[;,]', u.strip().strip('()')) if q.strip()]
            if len(parts) != 2: return 'format', 'Escribe dos valores separados por ; (ej: 2;3).'
            v = [_num(q) for q in parts]
            return ('ok', '') if all(abs(a - b) <= 1e-6 for a, b in zip(v, p['ans'])) else ('wrong', '')
        if t == 'expr':
            U = _ex(u)
            if simplify(U - _ex(p['ans'])) != 0: return 'wrong', ''
            if p.get('form') == 'expanded' and expand(U) != U: return 'incomplete', 'Es equivalente, pero falta desarrollar.'
            if p.get('form') == 'factored' and expand(U) == U: return 'incomplete', 'Es equivalente, pero falta factorizar.'
            return 'ok', ''
    except Exception:
        return 'format', 'No pude leer tu respuesta. Usa x, ^, *, / y paréntesis.'
    return 'format', ''

def sg(n): return f"+ {n}" if n >= 0 else f"- {-n}"

@tpl('M1-N2')
def _(r):
    p, d = r.choice([8000, 12000, 24000, 36000, 45000]), r.choice([10, 15, 20, 25, 30])
    return dict(text=f"Un producto cuesta ${p} y tiene {d}% de descuento. ¿Cuál es el precio final, en pesos?", type='num', ans=p * (100 - d) // 100,
        hints=["¿Qué porcentaje del precio original pagas realmente?", f"Pagas {100-d}% de {p}."], sol=f"Pagas {100-d}%: {p}·{100-d}/100 = {p*(100-d)//100}.")
@tpl('M1-N2', ctx=False)
def _(r):
    pc, b = r.choice([5, 15, 20, 40, 60]), r.choice([60, 80, 120, 200]); a = b * pc // 100
    return dict(text=f"¿Qué porcentaje de {b} es {a}? (responde solo el número)", type='num', ans=pc,
        hints=["Porcentaje = parte / total · 100.", f"Calcula {a}/{b} y multiplica por 100."], sol=f"{a}/{b}·100 = {pc}%.")
@tpl('M1-N3')
def _(r):
    b = r.choice([2, 3, 5]); m, n = r.randint(2, 6), r.randint(2, 6); c = r.randint(1, m + n - 1)
    return dict(text=f"Calcula el valor de ({b}^{m} · {b}^{n}) / {b}^{c}", type='num', ans=b ** (m + n - c),
        hints=["Misma base: al multiplicar se suman exponentes, al dividir se restan.", f"Queda {b}^({m}+{n}-{c})."], sol=f"{b}^{m+n-c} = {b**(m+n-c)}.")
@tpl('M1-A1')
def _(r):
    a = r.choice([1, 2, 3, 4, 5, -2, -3, -4])
    return dict(text=f"Desarrolla: (x {sg(a)})^2", type='expr', ans=f"x^2+{2*a}x+{a*a}", form='expanded',
        hints=["Cuadrado de binomio: (a+b)² = a² + 2ab + b².", f"a = x, b = {a}."], sol=f"x² + {2*a}x + {a*a}.")
@tpl('M1-A1')
def _(r):
    a, b = r.sample([1, 2, 3, 4, 5, 6, -1, -2, -3, -4], 2)
    return dict(text=f"Factoriza: x^2 {sg(a+b)}x {sg(a*b)}", type='expr', ans=f"(x+{a})(x+{b})", form='factored',
        hints=["Busca dos números que sumen el coeficiente de x y multipliquen al término libre.", f"Suman {a+b} y multiplican {a*b}."], sol=f"(x {sg(a)})(x {sg(b)}).")
@tpl('M1-A3')
def _(r):
    a, b, v = r.choice([2, 3, 4, 5, 6, -2, -3]), r.randint(-12, 12), r.randint(-9, 9)
    return dict(text=f"Resuelve: {a}x {sg(b)} = {a*v+b}", type='num', ans=v,
        hints=["Deja los términos con x a un lado y los números al otro.", f"Resta {b} a ambos lados y luego divide por {a}."], sol=f"{a}x = {a*v}, x = {v}.")
@tpl('M1-A3', ctx=True)
def _(r):
    F, k, n = r.choice([800, 1000, 1200]), r.choice([300, 400, 500]), r.randint(3, 15)
    return dict(text=f"Un taxi cobra ${F} fijos más ${k} por kilómetro. Un viaje costó ${F+k*n}. ¿Cuántos kilómetros recorrió?", type='num', ans=n,
        hints=["Plantea una ecuación: costo = fijo + tarifa·km.", f"{F} + {k}·x = {F+k*n}."], sol=f"{k}x = {k*n}, x = {n}.")
@tpl('M1-A3', skill='Argumentar')
def _(r):
    a, b, c = r.choice([2, 3, 4, 5]), r.randint(2, 9), r.randint(30, 60)
    return dict(text=f"Un estudiante resolvió {a}x + {b} = {c} así:\nPaso 1: {a}x + {b} = {c}\nPaso 2: {a}x = {c} + {b}\nPaso 3: x = {c+b}/{a}\n¿En qué paso (1, 2 o 3) está el primer error?", type='num', ans=2,
        hints=["Revisa qué operación se hace al pasar un término sumando al otro lado.", "Mira el signo en el paso 2."], sol=f"Paso 2: al pasar {b} restando queda {a}x = {c} − {b}.")
@tpl('M1-A4')
def _(r):
    while True:
        a1, b1, a2, b2 = [r.choice([1, 2, 3, -1, -2]) for _ in range(4)]
        if a1 * b2 - a2 * b1 != 0: break
    X, Y = r.randint(-4, 6), r.randint(-4, 6)
    return dict(text=f"Resuelve el sistema:\n{a1}x {sg(b1)}y = {a1*X+b1*Y}\n{a2}x {sg(b2)}y = {a2*X+b2*Y}\nResponde como x;y", type='pair', ans=(X, Y),
        hints=["Usa sustitución o reducción.", "Elimina una incógnita multiplicando las ecuaciones por números convenientes."], sol=f"x = {X}, y = {Y}.")
@tpl('M1-A5')
def _(r):
    m, x1, dx, y1 = r.randint(-5, 5), r.randint(-3, 3), r.randint(1, 4), r.randint(-5, 5)
    return dict(text=f"¿Cuál es la pendiente de la recta que pasa por ({x1}, {y1}) y ({x1+dx}, {y1+m*dx})?", type='num', ans=m,
        hints=["Pendiente = cambio en y / cambio en x.", f"Cambio en x: {dx}."], sol=f"{m*dx}/{dx} = {m}.")
@tpl('M1-A6')
def _(r):
    r1 = r.randint(1, 5); r2 = r.randint(r1 + 1, 8)
    return dict(text=f"Resuelve x^2 {sg(-(r1+r2))}x {sg(r1*r2)} = 0. Responde la solución menor.", type='num', ans=r1,
        hints=["Factoriza buscando dos números que sumen y multipliquen los coeficientes.", f"Suman {r1+r2}, multiplican {r1*r2}."], sol=f"(x−{r1})(x−{r2}) = 0, soluciones {r1} y {r2}.")
@tpl('M1-A6')
def _(r):
    h = r.randint(1, 6); c = r.randint(-5, 15)
    return dict(text=f"Halla el vértice de y = x^2 {sg(-2*h)}x {sg(c)}. Responde como x;y", type='pair', ans=(h, c - h * h),
        hints=["La coordenada x del vértice es −b/(2a).", f"x = {h}. Evalúa la función ahí."], sol=f"Vértice ({h}, {c-h*h}).")
@tpl('M1-G1', ctx=True)
def _(r):
    a, b, h = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17)]); k = r.randint(1, 3)
    return dict(text=f"Una escalera de {h*k} m apoyada en un muro llega a {b*k} m de altura. ¿A qué distancia del muro está su base, en metros?", type='num', ans=a * k,
        hints=["Forma un triángulo rectángulo: la escalera es la hipotenusa.", "a² + b² = c²."], sol=f"√({h*k}² − {b*k}²) = {a*k}.")
@tpl('M1-P3')
def _(r):
    t = r.choice([10, 20, 25, 40, 50]); rojo = r.randint(1, t - 1)
    return dict(text=f"Una urna tiene {rojo} bolas rojas y {t-rojo} azules. Se extrae una al azar. ¿Probabilidad de que sea roja? (fracción o decimal)", type='num', ans=rojo / t,
        hints=["Casos favorables / casos posibles.", f"Hay {t} bolas en total."], sol=f"{rojo}/{t} = {rojo/t}.")
@tpl('M2-N3')
def _(r):
    a, m, n, k = r.choice([(10, 4, 25, 2), (10, 5, 20, 2), (10, 25, 40, 3), (10, 2, 50, 2), (10, 8, 125, 3)])
    return dict(text=f"Calcula log_{a}({m}) + log_{a}({n})", type='num', ans=k,
        hints=["Suma de logaritmos de igual base = logaritmo del producto.", f"{m}·{n} = {m*n}."], sol=f"log({m*n}) = {k}.")
@tpl('M2-N3')
def _(r):
    b, k = r.choice([2, 3, 5]), r.randint(2, 4)
    return dict(text=f"Si log_{b}(x) = {k}, ¿cuánto vale x?", type='num', ans=b ** k,
        hints=["log_b(x) = k significa b^k = x."], sol=f"x = {b}^{k} = {b**k}.")

def par(n): return f"({n})" if n < 0 else str(n)

# ---- M1-N1 Enteros y racionales
@tpl('M1-N1')
def _(r):
    a, b, c, d = r.randint(-9, 9), r.randint(-9, 9), r.randint(2, 6), r.randint(-6, -2)
    return dict(text=f"Calcula: {a} − {par(b)} + {c} · {par(d)}", type='num', ans=a - b + c * d,
        hints=["Primero la multiplicación, luego izquierda a derecha.", "Restar un negativo equivale a sumar su opuesto."], sol=f"{a} + {-b} + {c*d} = {a-b+c*d}.")
@tpl('M1-N1')
def _(r):
    (a, b), (c, d) = r.choice([(1, 2), (3, 4), (1, 4), (3, 5), (7, 10)]), r.choice([(1, 2), (1, 4), (3, 4), (2, 5), (1, 10)])
    return dict(text=f"Calcula {a}/{b} + {c}/{d}. Responde como fracción o decimal.", type='num', ans=a / b + c / d,
        hints=["Busca un denominador común.", f"El común es {b*d}."], sol=f"{a/b} + {c/d} = {a/b+c/d}.")
@tpl('M1-N1', ctx=True)
def _(r):
    t, s, h, k = r.randint(-6, 0), r.randint(2, 4), r.randint(3, 6), r.randint(2, 8)
    return dict(text=f"A las 6:00 la temperatura era {t} °C. Subió {s} °C cada hora durante {h} horas y luego bajó {k} °C. ¿Cuál es la temperatura final, en °C?", type='num', ans=t + s * h - k,
        hints=["Calcula primero cuánto subió en total.", f"Subió {s}·{h} = {s*h}."], sol=f"{t} + {s*h} − {k} = {t+s*h-k}.")
# ---- M1-A2 Proporcionalidad
@tpl('M1-A2', ctx=True)
def _(r):
    k, n, m = r.choice([800, 1200, 1500, 2400]), r.randint(2, 5), r.randint(6, 12)
    return dict(text=f"{n} kg de manzanas cuestan ${k*n}. ¿Cuánto cuestan {m} kg, en pesos?", type='num', ans=k * m,
        hints=["Es proporcionalidad directa: busca el precio de 1 kg.", f"1 kg cuesta {k}."], sol=f"{k}·{m} = {k*m}.")
@tpl('M1-A2', ctx=True)
def _(r):
    w1, d, w2 = r.choice([(4, 12, 6), (6, 10, 5), (3, 20, 5), (8, 9, 6), (5, 12, 4)])
    return dict(text=f"{w1} obreros terminan una obra en {d} días. Trabajando al mismo ritmo, ¿en cuántos días la terminan {w2} obreros?", type='num', ans=w1 * d / w2,
        hints=["Más obreros, menos días: proporcionalidad inversa.", "El producto obreros·días es constante."], sol=f"{w1}·{d}/{w2} = {w1*d/w2}.")
@tpl('M1-A2')
def _(r):
    k, x0, x1 = r.randint(2, 9), r.randint(2, 6), r.randint(7, 15)
    return dict(text=f"y es directamente proporcional a x. Si x = {x0}, entonces y = {k*x0}. ¿Cuánto vale y cuando x = {x1}?", type='num', ans=k * x1,
        hints=["y/x es constante.", f"La constante es {k}."], sol=f"y = {k}·{x1} = {k*x1}.")
# ---- M1-G2 Cuerpos geométricos
@tpl('M1-G2')
def _(r):
    a = r.randint(2, 12)
    return dict(text=f"¿Cuál es el área total de la superficie de un cubo de arista {a} cm, en cm²?", type='num', ans=6 * a * a,
        hints=["Un cubo tiene 6 caras cuadradas iguales."], sol=f"6·{a}² = {6*a*a}.")
@tpl('M1-G2')
def _(r):
    R, h = r.randint(2, 6), r.randint(3, 10)
    return dict(text=f"Un cilindro tiene radio {R} cm y altura {h} cm. Su volumen en términos de π es (escribe, por ejemplo, 12pi):", type='expr', ans=f"{R*R*h}*pi",
        hints=["V = π · r² · h.", f"r² = {R*R}."], sol=f"{R*R*h}π cm³.")
@tpl('M1-G2', ctx=True)
def _(r):
    l, a, h = r.randint(4, 10), r.randint(3, 6), r.choice([1, 2])
    return dict(text=f"Una piscina rectangular mide {l} m de largo, {a} m de ancho y {h} m de profundidad. ¿Cuántos litros de agua caben? (1 m³ = 1000 litros)", type='num', ans=l * a * h * 1000,
        hints=["Calcula el volumen del paralelepípedo en m³.", f"{l}·{a}·{h} m³."], sol=f"{l*a*h} m³ = {l*a*h*1000} L.")
# ---- M1-G3 Transformaciones isométricas
@tpl('M1-G3')
def _(r):
    x0, y0, a, b = r.randint(-6, 6), r.randint(-6, 6), r.randint(-5, 5), r.randint(-5, 5)
    return dict(text=f"Se traslada el punto ({x0}, {y0}) con el vector ({a}, {b}). ¿Cuáles son las nuevas coordenadas? Responde como x;y", type='pair', ans=(x0 + a, y0 + b),
        hints=["Suma cada componente del vector a la coordenada correspondiente."], sol=f"({x0+a}, {y0+b}).")
@tpl('M1-G3')
def _(r):
    x0, y0 = r.choice([i for i in range(-7, 8) if i]), r.choice([i for i in range(-7, 8) if i]); eje = r.choice(['x', 'y'])
    return dict(text=f"Se refleja el punto ({x0}, {y0}) respecto al eje {eje}. ¿Cuáles son las nuevas coordenadas? Responde como x;y", type='pair', ans=(x0, -y0) if eje == 'x' else (-x0, y0),
        hints=["Al reflejar respecto a un eje, la coordenada perpendicular a él cambia de signo.", "Dibuja el punto y su simétrico."], sol=f"{(x0, -y0) if eje == 'x' else (-x0, y0)}.")
@tpl('M1-G3')
def _(r):
    x0, y0 = r.randint(-7, 7), r.randint(-7, 7)
    return dict(text=f"Se rota el punto ({x0}, {y0}) en 90° en sentido antihorario con centro en el origen. ¿Cuáles son las nuevas coordenadas? Responde como x;y", type='pair', ans=(-y0, x0),
        hints=["Una rotación de 90° antihoraria lleva (x, y) a un punto con las coordenadas intercambiadas y un signo cambiado.", "Prueba con el punto (1, 0): va a (0, 1)."], sol=f"(−y, x) = ({-y0}, {x0}).")
# ---- M1-P1 Tablas y gráficos
@tpl('M1-P1')
def _(r):
    m = r.randint(4, 9); dev = [r.randint(-3, 3) for _ in range(4)]; v = [m + d for d in dev] + [m - sum(dev)]; r.shuffle(v)
    return dict(text=f"Calcula el promedio de las notas: {', '.join(map(str, v))}", type='num', ans=m,
        hints=["Promedio = suma de los datos / cantidad de datos."], sol=f"Suma {sum(v)} / 5 = {m}.")
@tpl('M1-P1')
def _(r):
    n, f = r.choice([20, 25, 40, 50]), None; f = r.randint(2, n // 2)
    return dict(text=f"En un curso de {n} estudiantes, {f} prefieren matemática. ¿Cuál es la frecuencia relativa de esa preferencia? (decimal o fracción)", type='num', ans=f / n,
        hints=["Frecuencia relativa = frecuencia absoluta / total."], sol=f"{f}/{n} = {f/n}.")
@tpl('M1-P1')
def _(r):
    v = r.sample(range(1, 40), 7)
    return dict(text=f"Halla la mediana de los datos: {', '.join(map(str, v))}", type='num', ans=sorted(v)[3],
        hints=["Ordena los datos de menor a mayor.", "Con 7 datos, es el cuarto."], sol=f"Ordenados: {sorted(v)}; mediana {sorted(v)[3]}.")

# ---- M1-G4 Semejanza
@tpl('M1-G4', ctx=True)
def _(r):
    n, d = r.choice([10000, 25000, 50000, 100000]), r.randint(2, 9)
    return dict(text=f"En un mapa a escala 1:{n}, dos ciudades están a {d} cm. ¿Cuál es la distancia real, en metros?", type='num', ans=d * n / 100,
        hints=["Escala 1:n significa que 1 cm del mapa son n cm reales.", "Convierte de cm a m dividiendo por 100."], sol=f"{d}·{n} cm = {d*n/100} m.")
@tpl('M1-G4', ctx=True)
def _(r):
    h, s, S = r.randint(2, 4), r.choice([2, 3, 4, 5]), 0; S = s * r.randint(3, 8)
    return dict(text=f"Un poste de {h} m proyecta una sombra de {s} m. En el mismo instante, un árbol proyecta una sombra de {S} m. ¿Cuál es la altura del árbol, en metros?", type='num', ans=h * S / s,
        hints=["Los triángulos formados son semejantes.", "altura/sombra es igual en ambos."], sol=f"{h}/{s} = x/{S} → x = {h*S/s}.")
@tpl('M1-G4')
def _(r):
    k, A = r.randint(2, 5), r.randint(3, 12)
    return dict(text=f"Dos figuras son semejantes con razón de semejanza 1:{k}. Si la menor tiene área {A} cm², ¿cuál es el área de la mayor, en cm²?", type='num', ans=A * k * k,
        hints=["Las áreas se relacionan con el cuadrado de la razón de semejanza."], sol=f"{A}·{k}² = {A*k*k}.")
# ---- M1-P2 Medidas de posición
@tpl('M1-P2')
def _(r):
    v = r.sample(range(1, 40), 6); s = sorted(v)
    return dict(text=f"Halla la mediana de: {', '.join(map(str, v))}", type='num', ans=(s[2] + s[3]) / 2,
        hints=["Ordena los datos.", "Con cantidad par, promedia los dos centrales."], sol=f"Ordenados {s}; mediana {(s[2]+s[3])/2}.")
@tpl('M1-P2')
def _(r):
    q1 = r.randint(10, 40); q3 = q1 + r.randint(5, 30)
    return dict(text=f"En un diagrama de cajón, Q1 = {q1} y Q3 = {q3}. ¿Cuánto vale el rango intercuartil?", type='num', ans=q3 - q1,
        hints=["Rango intercuartil = Q3 − Q1."], sol=f"{q3} − {q1} = {q3-q1}.")
@tpl('M1-P2', ctx=True)
def _(r):
    n = r.choice([20, 40, 50, 100]); p = r.choice([10, 20, 25, 50, 80])
    return dict(text=f"En un grupo de {n} estudiantes, una nota está en el percentil {p}. ¿Cuántos estudiantes tienen una nota menor o igual a esa?", type='num', ans=n * p / 100,
        hints=["El percentil p deja aproximadamente p% de los datos por debajo."], sol=f"{p}% de {n} = {n*p/100}.")
# ---- M2-N1 Números reales
@tpl('M2-N1')
def _(r):
    a, b = r.choice([(2, 8), (3, 12), (5, 20), (2, 18), (8, 50), (3, 27)])
    return dict(text=f"Calcula √{a} · √{b}", type='num', ans=(a * b) ** 0.5, tol=1e-6,
        hints=["√a · √b = √(a·b).", f"{a}·{b} = {a*b}."], sol=f"√{a*b} = {(a*b)**0.5}.")
@tpl('M2-N1')
def _(r):
    a, b = r.randint(2, 7), r.choice([2, 3, 5, 6, 7])
    return dict(text=f"Escribe √{a*a*b} en la forma a√b con b lo menor posible. Responde como a;b", type='pair', ans=(a, b),
        hints=["Busca el mayor cuadrado perfecto que divide a la cantidad subradical.", f"{a*a*b} = {a*a}·{b}."], sol=f"{a}√{b}.")
# ---- M2-A1 Sistemas 2x2: tipos de solución
def _sis(r, same):
    a, b, c1, m = r.randint(1, 4), r.randint(1, 4), r.randint(2, 9), r.choice([2, 3, 4]); return a, b, c1, m
@tpl('M2-A1')
def _(r):
    a, b, c, m = _sis(r, False)
    return dict(text=f"Sistema: {a}x + {b}y = {c}  y  {a*m}x + ky = {m*c+1}. ¿Para qué valor de k NO tiene solución?", type='num', ans=b * m,
        hints=["Sin solución: rectas paralelas, mismos coeficientes proporcionales pero términos libres no proporcionales.", f"Multiplicas la primera ecuación por {m}."], sol=f"k = {b}·{m} = {b*m}.")
@tpl('M2-A1')
def _(r):
    a, b, c, m = _sis(r, True)
    return dict(text=f"Sistema: {a}x + {b}y = {c}  y  {a*m}x + ky = {m*c}. ¿Para qué valor de k tiene infinitas soluciones?", type='num', ans=b * m,
        hints=["Infinitas soluciones: la segunda ecuación es múltiplo de la primera.", f"El factor es {m}."], sol=f"k = {b*m}.")
@tpl('M2-A1', skill='Argumentar')
def _(r):
    a, b, c, m = _sis(r, True); caso = r.choice([0, 1, 2])
    k, c2 = {0: (b * m, m * c + 3), 1: (b * m + 1, m * c), 2: (b * m, m * c)}[caso]
    return dict(text=f"Sistema: {a}x + {b}y = {c}  y  {a*m}x + {k}y = {c2}.\nResponde 0 si no tiene solución, 1 si tiene una única solución, 2 si tiene infinitas.", type='num', ans={0: 0, 1: 1, 2: 2}[caso],
        hints=["Compara las razones entre coeficientes y términos libres.", f"La segunda ecuación se parece a {m} veces la primera."], sol=f"Respuesta: {caso}.")
# ---- M2-G2 Razones trigonométricas
@tpl('M2-G2')
def _(r):
    a, b, h = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17)]); k = r.randint(1, 3)
    return dict(text=f"En un triángulo rectángulo los catetos miden {a*k} y {b*k}. Si α es el ángulo opuesto al cateto de {a*k}, ¿cuánto vale sen α? (fracción o decimal)", type='num', ans=a / h,
        hints=["sen = cateto opuesto / hipotenusa.", "Calcula antes la hipotenusa con Pitágoras."], sol=f"Hipotenusa {h*k}; sen α = {a}/{h}.")
@tpl('M2-G2', ctx=True)
def _(r):
    k = r.randint(2, 9)
    return dict(text=f"Desde un punto a {4*k} m de la base de un edificio, el ángulo de elevación α cumple tan α = 3/4. ¿Qué altura tiene el edificio, en metros?", type='num', ans=3 * k,
        hints=["tan α = cateto opuesto / cateto adyacente.", "El cateto adyacente es la distancia a la base."], sol=f"h = {4*k}·3/4 = {3*k}.")
@tpl('M2-G2')
def _(r):
    a, b, h = r.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17)])
    return dict(text=f"En un triángulo rectángulo, el cateto adyacente a β mide {b} y la hipotenusa {h}. ¿Cuánto vale cos β? (fracción o decimal)", type='num', ans=b / h,
        hints=["cos = cateto adyacente / hipotenusa."], sol=f"{b}/{h}.")
# ---- M2-G4 Esfera / M2-G5 Rectas
@tpl('M2-G4')
def _(r):
    R = 3 * r.randint(1, 4)
    return dict(text=f"Volumen de una esfera de radio {R} cm, en términos de π (ej: 12pi):", type='expr', ans=f"{4*R**3//3}*pi",
        hints=["V = (4/3)·π·r³."], sol=f"{4*R**3//3}π cm³.")
@tpl('M2-G4')
def _(r):
    R = r.randint(2, 9)
    return dict(text=f"Área de la superficie de una esfera de radio {R} cm, en términos de π:", type='expr', ans=f"{4*R*R}*pi",
        hints=["A = 4·π·r²."], sol=f"{4*R*R}π cm².")
@tpl('M2-G5')
def _(r):
    m, x0, y0 = r.choice([-3, -2, 2, 3, 4]), r.randint(-4, 4), r.randint(-6, 6)
    return dict(text=f"La recta L tiene ecuación y = {m}x + 1. Una recta paralela a L pasa por ({x0}, {y0}). Si su ecuación es y = {m}x + n, ¿cuánto vale n?", type='num', ans=y0 - m * x0,
        hints=["Rectas paralelas tienen igual pendiente.", "Reemplaza el punto en la ecuación."], sol=f"n = {y0} − ({m})·({x0}) = {y0-m*x0}.")
@tpl('M2-G5')
def _(r):
    m = r.choice([2, 4, 5, -2, -4, -5])
    return dict(text=f"Una recta tiene pendiente {m}. ¿Cuál es la pendiente de una recta perpendicular a ella? (fracción o decimal)", type='num', ans=-1 / m,
        hints=["Si dos rectas son perpendiculares, el producto de sus pendientes es −1."], sol=f"−1/({m}) = {-1/m}.")
# ---- M2-P1 Dispersión / M2-P3 Combinatoria
@tpl('M2-P1')
def _(r):
    m, a, b = r.randint(10, 30), *r.choice([(1, 3), (2, 4), (1, 5), (3, 5)])
    v = [m - a, m + a, m - b, m + b]; r.shuffle(v)
    return dict(text=f"Calcula la varianza poblacional de los datos: {', '.join(map(str, v))}", type='num', ans=(a * a + b * b) / 2,
        hints=["Varianza = promedio de los cuadrados de las desviaciones respecto al promedio.", f"El promedio es {m}."], sol=f"({a}²+{a}²+{b}²+{b}²)/4 = {(a*a+b*b)/2}.")
@tpl('M2-P1')
def _(r):
    m, a = r.randint(10, 30), r.randint(2, 6)
    return dict(text=f"Calcula la desviación estándar poblacional de: {m-a}, {m+a}, {m-a}, {m+a}", type='num', ans=a,
        hints=["Desviación estándar = raíz de la varianza.", "Todas las desviaciones valen lo mismo en valor absoluto."], sol=f"σ = {a}.")
@tpl('M2-P3')
def _(r):
    n = r.randint(4, 6)
    import math
    return dict(text=f"¿De cuántas formas distintas pueden ordenarse {n} libros distintos en un estante?", type='num', ans=math.factorial(n),
        hints=["Permutaciones de n objetos distintos: n!"], sol=f"{n}! = {math.factorial(n)}.")
@tpl('M2-P3', ctx=True)
def _(r):
    import math
    n, k = r.choice([(6, 2), (7, 3), (8, 3), (10, 2), (9, 4)])
    return dict(text=f"De un curso de {n} estudiantes se elige un comité de {k} personas sin importar el orden. ¿Cuántos comités distintos hay?", type='num', ans=math.comb(n, k),
        hints=["Si el orden no importa, es una combinación: C(n,k) = n!/(k!(n−k)!)."], sol=f"C({n},{k}) = {math.comb(n,k)}.")
@tpl('M2-P3', ctx=True)
def _(r):
    import math
    n, k = r.choice([(5, 2), (6, 3), (8, 2), (7, 3)])
    return dict(text=f"En una carrera participan {n} atletas. ¿De cuántas maneras pueden repartirse el 1.º, 2.º y 3.º lugar?" if k == 3 else f"Entre {n} candidatos se eligen presidente y secretario (cargos distintos). ¿De cuántas formas?", type='num', ans=math.perm(n, 3 if k == 3 else 2),
        hints=["Aquí el orden importa: permutación P(n,k) = n!/(n−k)!."], sol=f"{math.perm(n, 3 if k == 3 else 2)}.")

# ---- M2-A2 Funciones potencia, exponencial y logarítmica
@tpl('M2-A2')
def _(r):
    a, b, n = r.randint(1, 5), r.choice([2, 3, 4]), r.randint(2, 4)
    return dict(text=f"Si f(x) = {a}·{b}^x, ¿cuánto vale f({n})?", type='num', ans=a * b ** n, hints=["Reemplaza x por el valor y calcula la potencia primero."], sol=f"{a}·{b**n//1} = {a*b**n}.".replace(f"{a}·{b**n//1}", f"{a}·{b}^{n}"))
@tpl('M2-A2', ctx=True)
def _(r):
    n0, t = r.choice([50, 100, 200, 500]), r.randint(3, 6)
    return dict(text=f"Un cultivo de {n0} bacterias duplica su cantidad cada hora: N(t) = {n0}·2^t. ¿Cuántas bacterias hay después de {t} horas?", type='num', ans=n0 * 2 ** t,
        hints=["Reemplaza t en la fórmula.", f"2^{t} = {2**t}."], sol=f"{n0}·{2**t} = {n0*2**t}.")
@tpl('M2-A2')
def _(r):
    b, k = r.choice([2, 3, 5]), r.randint(2, 4)
    return dict(text=f"Si f(x) = log_{b}(x), ¿cuánto vale f({b**k})?", type='num', ans=k, hints=["¿A qué exponente hay que elevar la base para obtener el número?"], sol=f"{b}^{k} = {b**k}, entonces f = {k}.")
@tpl('M2-A2')
def _(r):
    b, k = r.choice([2, 3, 4]), r.randint(-3, 5)
    return dict(text=f"¿En qué punto corta al eje y la gráfica de y = {b}^x {sg(k)}? Responde como x;y", type='pair', ans=(0, 1 + k), hints=["El corte con el eje y se obtiene con x = 0.", "Cualquier base elevada a 0 vale 1."], sol=f"(0, {1+k}).")
# ---- M2-A3 Funciones seno y coseno
@tpl('M2-A3')
def _(r):
    A, B = r.randint(2, 6), r.choice([1, 2, 4])
    return dict(text=f"¿Cuál es el período de f(x) = {A}·sen({B}x)? Responde en términos de π (ej: 2pi).", type='expr', ans=f"2*pi/{B}", hints=["Período de sen(Bx) = 2π/B."], sol=f"2π/{B}.")
@tpl('M2-A3')
def _(r):
    A, k = r.randint(2, 6), r.randint(-3, 4)
    return dict(text=f"¿Cuál es el valor máximo de f(x) = {A}·cos(x) {sg(k)}?", type='num', ans=A + k, hints=["El coseno oscila entre −1 y 1.", "El máximo ocurre cuando cos x = 1."], sol=f"{A}·1 {sg(k)} = {A+k}.")
@tpl('M2-A3')
def _(r):
    f, ang, v = r.choice([('sen', 30, 0.5), ('cos', 60, 0.5), ('sen', 90, 1), ('cos', 180, -1), ('cos', 90, 0), ('sen', 0, 0), ('cos', 0, 1)])
    return dict(text=f"¿Cuánto vale {f} {ang}°? (decimal o fracción)", type='num', ans=v, hints=["Recuerda los valores notables en la circunferencia unitaria."], sol=f"{f} {ang}° = {v}.")
# ---- M2-G1 Homotecia
@tpl('M2-G1')
def _(r):
    k, L = r.choice([2, 3, 4, 0.5]), r.choice([4, 6, 8, 10])
    return dict(text=f"Una homotecia de razón {k} transforma un segmento de {L} cm. ¿Cuánto mide su imagen, en cm?", type='num', ans=k * L, hints=["Las longitudes se multiplican por el valor absoluto de la razón."], sol=f"{k}·{L} = {k*L}.")
@tpl('M2-G1')
def _(r):
    k, x0, y0 = r.choice([2, 3, -1, -2]), r.randint(-5, 5), r.randint(-5, 5)
    return dict(text=f"Se aplica una homotecia de centro en el origen y razón {k} al punto ({x0}, {y0}). ¿Cuál es la imagen? Responde como x;y", type='pair', ans=(k * x0, k * y0), hints=["Multiplica ambas coordenadas por la razón."], sol=f"({k*x0}, {k*y0}).")
@tpl('M2-G1')
def _(r):
    k, A = r.choice([2, 3, 4]), r.randint(2, 9)
    return dict(text=f"Una figura de área {A} cm² se transforma con una homotecia de razón {k}. ¿Cuál es el área de la imagen, en cm²?", type='num', ans=A * k * k, hints=["Las áreas se multiplican por el cuadrado de la razón."], sol=f"{A}·{k}² = {A*k*k}.")
# ---- M2-G3 Circunferencia
@tpl('M2-G3')
def _(r):
    a = r.randint(15, 70)
    return dict(text=f"Un ángulo del centro mide {2*a}°. ¿Cuánto mide un ángulo inscrito que subtiende el mismo arco, en grados?", type='num', ans=a, hints=["El ángulo inscrito mide la mitad del ángulo del centro."], sol=f"{2*a}/2 = {a}.")
@tpl('M2-G3')
def _(r):
    a, b, c = r.choice([(6, 4, 3), (8, 3, 6), (10, 3, 5), (12, 2, 4), (9, 4, 6)])
    return dict(text=f"Dos cuerdas se cortan en un punto P. En la primera, los segmentos miden {a} y {b}. En la segunda, un segmento mide {c}. ¿Cuánto mide el otro segmento?", type='num', ans=a * b / c, hints=["Producto de segmentos de una cuerda = producto de segmentos de la otra."], sol=f"{a}·{b}/{c} = {a*b/c}.")
@tpl('M2-G3')
def _(r):
    t, a = r.choice([(6, 4), (6, 3), (8, 4), (10, 4), (12, 8)])
    return dict(text=f"Desde un punto exterior P se traza una tangente PT y una secante que corta la circunferencia en A y B, con PA = {a} y AB = {t*t//a - a}. ¿Cuánto mide PT?", type='num', ans=t, hints=["Tangente² = (segmento externo)·(secante completa).", f"La secante completa mide PA + AB = {t*t//a}."], sol=f"PT² = {a}·{t*t//a} = {t*t}, PT = {t}.")
# ---- M2-N2 Matemática financiera
@tpl('M2-N2', ctx=True)
def _(r):
    p, n = r.choice([10, 20]), r.randint(2, 3)
    return dict(text=f"Inviertes $1.000.000 con interés compuesto anual de {p}% durante {n} años. ¿Cuánto tienes al final, en pesos? (escribe sin puntos)", type='num', ans=round(1000000 * (1 + p / 100) ** n),
        hints=["Capital final = C·(1 + r)^n.", f"Factor anual: {1+p/100}."], sol=f"1000000·{1+p/100}^{n} = {round(1000000*(1+p/100)**n)}.")
@tpl('M2-N2', ctx=True)
def _(r):
    C, i, t = r.choice([200000, 500000, 800000]), r.choice([2, 3, 4]), r.randint(3, 12)
    return dict(text=f"Un crédito de ${C} cobra interés simple de {i}% mensual. ¿Cuánto interés se paga en {t} meses, en pesos? (sin puntos)", type='num', ans=C * i * t // 100, hints=["Interés simple = C · tasa · tiempo."], sol=f"{C}·{i/100}·{t} = {C*i*t//100}.")
@tpl('M2-N2', ctx=True)
def _(r):
    S, p = r.choice([600000, 800000, 1000000, 1500000]), 10
    return dict(text=f"Una persona cotiza {p}% de su sueldo mensual de ${S} en su AFP. ¿Cuánto aporta en 12 meses, en pesos? (sin puntos)", type='num', ans=S * p // 100 * 12, hints=["Primero calcula el aporte de un mes."], sol=f"{S*p//100}·12 = {S*p//100*12}.")
# ---- M2-P2 Probabilidad condicional
@tpl('M2-P2')
def _(r):
    pb, c = r.choice([0.2, 0.4, 0.5, 0.8]), r.choice([0.25, 0.5, 0.75, 0.2])
    return dict(text=f"P(B) = {pb} y P(A ∩ B) = {round(pb*c,4)}. ¿Cuánto vale P(A | B)? (decimal o fracción)", type='num', ans=c, hints=["P(A|B) = P(A ∩ B) / P(B)."], sol=f"{round(pb*c,4)}/{pb} = {c}.")
@tpl('M2-P2', ctx=True)
def _(r):
    t, rj = r.choice([(10, 4), (8, 3), (6, 4), (9, 5)])
    return dict(text=f"Una urna tiene {t} bolas, {rj} rojas. Se sacan 2 sin reposición. ¿Probabilidad de que ambas sean rojas? Responde como fracción (ej: 2/15).", type='num', ans=rj / t * (rj - 1) / (t - 1), hints=["Sin reposición: la segunda extracción es condicional a la primera.", f"P(1.ª roja) = {rj}/{t}; luego quedan {t-1} bolas."], sol=f"{rj}/{t}·{rj-1}/{t-1}.")
# ---- M2-P4 Modelos probabilísticos
@tpl('M2-P4')
def _(r):
    import math
    n, k = r.choice([(3, 2), (4, 2), (4, 3), (3, 1), (4, 1)])
    return dict(text=f"Se lanza {n} veces una moneda justa. ¿Probabilidad de obtener exactamente {k} caras? (fracción o decimal)", type='num', ans=math.comb(n, k) / 2 ** n, hints=["Binomial: C(n,k)·p^k·(1−p)^(n−k).", "Aquí p = 1/2."], sol=f"C({n},{k})/2^{n} = {math.comb(n,k)/2**n}.")
@tpl('M2-P4')
def _(r):
    n, p = r.choice([50, 80, 100, 200]), r.choice([0.1, 0.2, 0.25, 0.5])
    return dict(text=f"X sigue una distribución binomial con n = {n} y p = {p}. ¿Cuánto vale su esperanza (media)?", type='num', ans=n * p, hints=["E(X) = n·p."], sol=f"{n}·{p} = {n*p}.")
@tpl('M2-P4')
def _(r):
    m, s, z = r.randint(50, 100), r.choice([5, 10, 15]), r.randint(-2, 3)
    return dict(text=f"X ~ N(μ = {m}, σ = {s}). ¿Cuál es el valor estandarizado (z) de x = {m+z*s}?", type='num', ans=z, hints=["z = (x − μ)/σ."], sol=f"({m+z*s} − {m})/{s} = {z}.")
@tpl('M2-P4')
def _(r):
    k = r.choice([1, 2, 3])
    return dict(text=f"En una distribución normal, ¿qué porcentaje aproximado de los datos está a menos de {k} desviación(es) estándar de la media, según la regla empírica 68–95–99,7?", type='num', ans={1: 68, 2: 95, 3: 99.7}[k], tol=1e-6, hints=["Recuerda los tres porcentajes de la regla."], sol=f"{ {1:68,2:95,3:99.7}[k] }%.")
