"""
LATIPOV GAME — Multiplayer WebSocket Server
Flask-SocketIO with room-based lobby system
"""
import random, string, time
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'latipov-game-ws-secret-2024'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ── In-memory rooms ──────────────────────────────────────────────
rooms   = {}   # code → RoomState
players = {}   # sid  → { room_code, username, color, team }

DIFF_CFG = {
    'easy':   {'t': 15, 'q': 10, 'max': 12,  'ops': ['+', '-'],            'base': 10},
    'medium': {'t': 12, 'q': 10, 'max': 25,  'ops': ['+', '-', '×'],       'base': 20},
    'hard':   {'t': 10, 'q': 10, 'max': 50,  'ops': ['+', '-', '×', '÷'], 'base': 30},
}

def gen_code():
    while True:
        c = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if c not in rooms:
            return c

def gen_question(cfg):
    ops = cfg['ops']
    op  = random.choice(ops)
    mx  = cfg['max']
    if op == '+': a = random.randint(1,mx);  b = random.randint(1,mx);       ans = a+b
    elif op=='-': a = random.randint(2,mx);  b = random.randint(1,a);         ans = a-b
    elif op=='×': a = random.randint(2,min(mx,12)); b=random.randint(2,min(mx,12)); ans=a*b
    else:         b = random.randint(2,min(mx,12)); ans=random.randint(2,min(mx,12)); a=b*ans
    # 2 choices
    delta = random.randint(1, max(3, abs(ans)//3 + 2))
    wrong = ans + delta if random.random() > .5 else ans - delta
    if wrong < 0 or wrong == ans: wrong = ans + 1
    choices = [ans, wrong]
    random.shuffle(choices)
    return {'text': f'{a} {op} {b} = ?', 'ans': ans, 'choices': choices}

class RoomState:
    def __init__(self, code, host_sid, difficulty, host_name, host_color):
        self.code       = code
        self.host_sid   = host_sid
        self.difficulty = difficulty
        self.cfg        = DIFF_CFG[difficulty]
        self.host_name  = host_name
        self.host_color = host_color
        self.guest_sid  = None
        self.guest_name = None
        self.guest_color= None
        self.started    = False
        self.qi         = 0
        self.flag_pos   = 0   # -5 … +5
        self.host_score = 0
        self.guest_score= 0
        self.cur_q      = None
        self.answered   = {}  # sid → bool
        self.timer_task = None
        self.start_time = None

    def both_connected(self):
        return self.guest_sid is not None

    def to_lobby_info(self):
        return {
            'code': self.code,
            'host': self.host_name,
            'difficulty': self.difficulty,
            'waiting': self.guest_sid is None,
        }

# ── Socket events ─────────────────────────────────────────────────

@socketio.on('connect')
def on_connect():
    print(f'[+] connected: {request.sid}')

@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    if sid not in players: return
    info = players.pop(sid)
    code = info['room_code']
    if code not in rooms: return
    room = rooms[code]
    # Notify other player
    if room.host_sid == sid:
        other = room.guest_sid
    else:
        other = room.host_sid
    if other:
        emit('opponent_left', {}, to=other)
    del rooms[code]
    print(f'[-] room {code} closed')

@socketio.on('create_room')
def on_create(data):
    sid  = request.sid
    name = (data.get('username') or 'Player')[:20]
    color= data.get('color', '#00d4ff')
    diff = data.get('difficulty', 'medium')
    if diff not in DIFF_CFG: diff = 'medium'
    code = gen_code()
    rooms[code]   = RoomState(code, sid, diff, name, color)
    players[sid]  = {'room_code': code, 'username': name, 'color': color, 'team': 'blue'}
    join_room(code)
    emit('room_created', {'code': code, 'difficulty': diff})
    print(f'[room] {code} created by {name}')

@socketio.on('join_room_req')
def on_join(data):
    sid   = request.sid
    code  = (data.get('code') or '').strip().upper()
    name  = (data.get('username') or 'Player')[:20]
    color = data.get('color', '#ff5e7a')
    if code not in rooms:
        emit('join_error', {'msg': 'Room not found. Check the code!'})
        return
    room = rooms[code]
    if room.guest_sid:
        emit('join_error', {'msg': 'Room is full!'})
        return
    if room.started:
        emit('join_error', {'msg': 'Game already started!'})
        return
    room.guest_sid   = sid
    room.guest_name  = name
    room.guest_color = color
    players[sid] = {'room_code': code, 'username': name, 'color': color, 'team': 'red'}
    join_room(code)
    # Notify both
    state = {
        'host':  {'name': room.host_name,  'color': room.host_color,  'score': 0, 'team': 'blue'},
        'guest': {'name': room.guest_name, 'color': room.guest_color, 'score': 0, 'team': 'red'},
        'difficulty': room.difficulty,
        'code': code,
    }
    emit('player_joined', state, to=room.host_sid)
    emit('joined_ok',     state)
    # Auto-start after 1s countdown
    socketio.sleep(1.5)
    start_round(room)

def start_round(room):
    room.started   = True
    room.cur_q     = gen_question(room.cfg)
    room.answered  = {}
    room.start_time= time.time()
    room.qi += 1
    payload = {
        'question': room.cur_q['text'],
        'choices' : room.cur_q['choices'],
        'qi': room.qi, 'total': room.cfg['q'],
        'timer': room.cfg['t'],
        'flag_pos': room.flag_pos,
        'host_score': room.host_score,
        'guest_score': room.guest_score,
    }
    socketio.emit('round_start', payload, to=room.code)
    # Timer
    def timer_cb():
        socketio.sleep(room.cfg['t'])
        if room.code in rooms and rooms[room.code].cur_q == room.cur_q:
            handle_timeout(room)
    socketio.start_background_task(timer_cb)

def handle_timeout(room):
    # No answer — flag stays, move to next
    process_round_end(room, None)

@socketio.on('submit_answer')
def on_answer(data):
    sid    = request.sid
    if sid not in players: return
    info   = players[sid]
    code   = info['room_code']
    if code not in rooms: return
    room   = rooms[code]
    if sid in room.answered: return   # already answered this round
    room.answered[sid] = data.get('answer')
    # If both answered, resolve immediately
    both = {room.host_sid, room.guest_sid} - {None}
    if set(room.answered.keys()) >= both:
        process_round_end(room, None)

def process_round_end(room, _):
    if room.code not in rooms: return
    ans = room.cur_q['ans']
    host_correct  = room.answered.get(room.host_sid)  == ans
    guest_correct = room.answered.get(room.guest_sid) == ans

    STEP = 8
    MAX  = 5
    BASE = room.cfg['base']

    if host_correct and not guest_correct:
        room.flag_pos   = min(MAX, room.flag_pos + 1)
        room.host_score += BASE
    elif guest_correct and not host_correct:
        room.flag_pos    = max(-MAX, room.flag_pos - 1)
        room.guest_score += BASE
    elif host_correct and guest_correct:
        room.host_score  += BASE
        room.guest_score += BASE

    result = {
        'host_correct':  host_correct,
        'guest_correct': guest_correct,
        'correct_ans':   ans,
        'flag_pos':      room.flag_pos,
        'flag_pct':      50 + room.flag_pos * STEP,
        'host_score':    room.host_score,
        'guest_score':   room.guest_score,
        'qi': room.qi, 'total': room.cfg['q'],
    }
    socketio.emit('round_result', result, to=room.code)

    # Check win by flag
    if room.flag_pos >= MAX:
        socketio.sleep(.9)
        end_game(room, 'host')
        return
    if room.flag_pos <= -MAX:
        socketio.sleep(.9)
        end_game(room, 'guest')
        return
    # Check questions exhausted
    if room.qi >= room.cfg['q']:
        winner = 'host' if room.flag_pos > 0 else ('guest' if room.flag_pos < 0 else 'draw')
        socketio.sleep(.9)
        end_game(room, winner)
        return
    # Next round
    socketio.sleep(1.0)
    start_round(room)

def end_game(room, winner):
    payload = {
        'winner': winner,
        'host_score':  room.host_score,
        'guest_score': room.guest_score,
        'host_name':   room.host_name,
        'guest_name':  room.guest_name,
        'flag_pos':    room.flag_pos,
    }
    socketio.emit('game_over', payload, to=room.code)
    if room.code in rooms:
        del rooms[room.code]

@app.route('/health')
def health():
    return {'status': 'ok', 'rooms': len(rooms)}

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
