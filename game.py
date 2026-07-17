"""
Morabaraba — Southern African Strategy Game
Python/Tkinter port with Q-Learning AI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json, math, random, threading, time
from copy import deepcopy

# ═══════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════

EMPTY, P1, P2 = 0, 1, 2
PHASE_PLACING, PHASE_MOVING, PHASE_OVER = "placing", "moving", "over"

ADJACENCY = {
    0:[1,7,8],   1:[0,2,9],   2:[1,3,10],  3:[2,4,11],
    4:[3,5,12],  5:[4,6,13],  6:[5,7,14],  7:[0,6,15],
    8:[9,15,0,16], 9:[8,10,17], 10:[9,11,2,18], 11:[10,12,3,19],
    12:[11,13,4,20],13:[12,14,5,21],14:[13,15,6,22],15:[14,8,7,23],
    16:[17,23,8],17:[16,18,9],18:[17,19,10],19:[18,20,11],
    20:[19,21,12],21:[20,22,13],22:[21,23,14],23:[22,16,15]
}

MILLS = [
    [0,1,2],[2,3,4],[4,5,6],[6,7,0],
    [8,9,10],[10,11,12],[12,13,14],[14,15,8],
    [16,17,18],[18,19,20],[20,21,22],[22,23,16],
    [1,9,17],[3,11,19],[5,13,21],[7,15,23],
    [0,8,16],[2,10,18],[4,12,20],[6,14,22]
]

# Board node coordinates (3 concentric squares)
W, H = 560, 560
CX, CY = 280, 280

def compute_positions():
    pos = []
    for r in [240, 160, 80]:
        corners = [(0,0),(0.5,0),(1,0),(1,0.5),(1,1),(0.5,1),(0,1),(0,0.5)]
        for fx, fy in corners:
            pos.append((CX - r + fx*2*r, CY - r + fy*2*r))
    return pos

POS = compute_positions()

# Colours
BG_DARK      = "#1c0f05"
WOOD_DARK    = "#3d2008"
WOOD_MID     = "#6b3a1f"
WOOD_LIGHT   = "#a0582a"
GOLD         = "#c9943a"
GOLD_LIGHT   = "#e8c46a"
CREAM        = "#f5e6c8"
TEXT_MUTED   = "#a08060"
P1_BASE      = "#1a1a2e"
P1_BORDER    = "#8a8ade"
P2_BASE      = "#6a1010"
P2_BORDER    = "#e08080"
PANEL_BG     = "#2a1508"
LINE_COL     = "#5a3010"
LINE_DIAG    = "#6a3a14"


# ═══════════════════════════════════════════════════════
# GAME ENGINE
# ═══════════════════════════════════════════════════════

class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [EMPTY] * 24
        self.current = P1
        self.hand = {P1: 12, P2: 12}
        self.phase = PHASE_PLACING
        self.must_shoot = False
        self.winner = None
        self.move_count = 0
        self.prev_mills = {P1: set(), P2: set()}
        return self

    def clone(self):
        g = Game.__new__(Game)
        g.board = self.board[:]
        g.current = self.current
        g.hand = dict(self.hand)
        g.phase = self.phase
        g.must_shoot = self.must_shoot
        g.winner = self.winner
        g.move_count = self.move_count
        g.prev_mills = {P1: set(self.prev_mills[P1]), P2: set(self.prev_mills[P2])}
        return g

    def opp(self, p): return P2 if p == P1 else P1

    def count_cows(self, p): return self.board.count(p)

    def total_cows(self, p): return self.count_cows(p) + self.hand[p]

    def active_mills(self, p):
        result = set()
        for mill in MILLS:
            if all(self.board[i] == p for i in mill):
                result.add(tuple(mill))
        return result

    def new_mill_formed(self, p, pos):
        for mill in MILLS:
            if pos in mill and all(self.board[i] == p for i in mill):
                key = tuple(mill)
                if key not in self.prev_mills[p]:
                    return True
        return False

    def in_any_mill(self, pos, p):
        return any(pos in m and all(self.board[i] == p for i in m) for m in MILLS)

    def get_legal_moves(self):
        p, opp = self.current, self.opp(self.current)
        if self.phase == PHASE_OVER:
            return []
        if self.must_shoot:
            targets = [i for i in range(24) if self.board[i] == opp]
            non_mill = [i for i in targets if not self.in_any_mill(i, opp)]
            pick = non_mill if non_mill else targets
            return [{"t": "shoot", "pos": i} for i in pick]
        if self.phase == PHASE_PLACING:
            if self.hand[p] <= 0:
                return []
            return [{"t": "place", "pos": i} for i in range(24) if self.board[i] == EMPTY]
        moves = []
        flying = self.count_cows(p) <= 3
        for s in range(24):
            if self.board[s] != p:
                continue
            dests = [i for i in range(24) if self.board[i] == EMPTY] if flying \
                    else [i for i in ADJACENCY[s] if self.board[i] == EMPTY]
            for d in dests:
                moves.append({"t": "move", "from": s, "to": d})
        return moves

    def apply(self, move):
        p = self.current
        self.move_count += 1
        if move["t"] == "shoot":
            self.board[move["pos"]] = EMPTY
            self.must_shoot = False
            self.prev_mills[p] = self.active_mills(p)
            self.prev_mills[self.opp(p)] = self.active_mills(self.opp(p))
            self._switch_turn()
            self._check_over()
            return self
        if move["t"] == "place":
            self.board[move["pos"]] = p
            self.hand[p] -= 1
            formed = self.new_mill_formed(p, move["pos"])
            self.prev_mills[p] = self.active_mills(p)
            if formed and self.count_cows(self.opp(p)) > 0:
                self.must_shoot = True
            else:
                if self.hand[P1] == 0 and self.hand[P2] == 0:
                    self.phase = PHASE_MOVING
                self._switch_turn()
            self._check_over()
            return self
        if move["t"] == "move":
            self.board[move["from"]] = EMPTY
            self.board[move["to"]] = p
            formed = self.new_mill_formed(p, move["to"])
            self.prev_mills[p] = self.active_mills(p)
            if formed and self.count_cows(self.opp(p)) > 0:
                self.must_shoot = True
            else:
                self._switch_turn()
            self._check_over()
            return self

    def _switch_turn(self):
        self.current = self.opp(self.current)

    def _check_over(self):
        if self.phase == PHASE_OVER:
            return
        for p in [P1, P2]:
            if self.total_cows(self.opp(p)) < 3:
                self.phase = PHASE_OVER
                self.winner = p
                return
        if self.phase == PHASE_MOVING and not self.must_shoot and not self.get_legal_moves():
            self.phase = PHASE_OVER
            self.winner = self.opp(self.current)

    def state_key(self):
        return "".join(map(str, self.board)) + f"|{self.current}|{self.hand[P1]}|{self.hand[P2]}|{1 if self.must_shoot else 0}|{self.phase}"


# ═══════════════════════════════════════════════════════
# Q-LEARNING AGENT
# ═══════════════════════════════════════════════════════

class QAgent:
    def __init__(self, player, alpha=0.2, gamma=0.95, epsilon=0.9,
                 epsilon_min=0.05, epsilon_decay=0.9995):
        self.player = player
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q = {}
        self.episodes = 0
        self.wins = self.losses = self.draws = 0

    @staticmethod
    def _mk(sk, move): return sk + "~" + json.dumps(move, sort_keys=True)

    def get_q(self, sk, m): return self.q.get(self._mk(sk, m), 0.0)

    def set_q(self, sk, m, v): self.q[self._mk(sk, m)] = v

    def choose(self, game, training=False):
        moves = game.get_legal_moves()
        if not moves:
            return None
        if training and random.random() < self.epsilon:
            return random.choice(moves)
        sk = game.state_key()
        best, best_moves = -float("inf"), []
        for m in moves:
            qv = self.get_q(sk, m)
            if qv > best:
                best, best_moves = qv, [m]
            elif qv == best:
                best_moves.append(m)
        return random.choice(best_moves)

    def learn(self, sk, m, r, nsk, next_moves, done):
        old = self.get_q(sk, m)
        if done or not next_moves:
            target = r
        else:
            target = r + self.gamma * max(self.get_q(nsk, nm) for nm in next_moves)
        self.set_q(sk, m, old + self.alpha * (target - old))

    def decay(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    @property
    def q_size(self): return len(self.q)

    @property
    def win_rate(self):
        t = self.wins + self.losses + self.draws
        return self.wins / t if t else 0.0

    def to_dict(self):
        return {"q": list(self.q.items()), "epsilon": self.epsilon,
                "episodes": self.episodes, "wins": self.wins,
                "losses": self.losses, "draws": self.draws}

    def from_dict(self, d):
        self.q = dict(d["q"])
        self.epsilon = d["epsilon"]
        self.episodes = d["episodes"]
        self.wins = d["wins"]
        self.losses = d["losses"]
        self.draws = d["draws"]


def reward(before, move, after, p):
    r = -0.01
    if after.phase == PHASE_OVER:
        return 1.0 if after.winner == p else (-1.0 if after.winner else -0.2)
    if move["t"] == "shoot":
        r += 0.3
    if move["t"] in ("place", "move"):
        if len(after.active_mills(p)) > len(before.active_mills(p)):
            r += 0.1
    return r


def self_play_episode(a1, a2):
    game = Game()
    hist1, hist2 = [], []
    for _ in range(300):
        if game.phase == PHASE_OVER:
            break
        agent = a1 if game.current == P1 else a2
        hist = hist1 if game.current == P1 else hist2
        p = game.current
        sk = game.state_key()
        move = agent.choose(game, training=True)
        if not move:
            break
        before = game.clone()
        game.apply(move)
        r = reward(before, move, game, p)
        hist.append((sk, move, r))

    winner = game.winner

    def backprop(hist, agent, my_p):
        for i, (sk, move, r) in enumerate(hist):
            if i < len(hist) - 1:
                nsk, nm, _ = hist[i + 1]
                agent.learn(sk, move, r, nsk, [nm], False)
            else:
                fr = 1.0 if winner == my_p else (-1.0 if winner else -0.2)
                agent.learn(sk, move, fr, sk, [], True)
        agent.decay()

    backprop(hist1, a1, P1)
    backprop(hist2, a2, P2)
    if winner == P1:
        a1.wins += 1; a2.losses += 1
    elif winner == P2:
        a2.wins += 1; a1.losses += 1
    else:
        a1.draws += 1; a2.draws += 1
    a1.episodes += 1
    return winner


# ═══════════════════════════════════════════════════════
# TKINTER GUI
# ═══════════════════════════════════════════════════════

class MorabarabaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Morabaraba — Southern African Strategy Game")
        self.configure(bg=BG_DARK)
        self.resizable(False, False)

        # State
        self.mode = "human"   # "human" | "aivsai"
        self.game = Game()
        self.agent1 = QAgent(P1)
        self.agent2 = QAgent(P2)
        self.selected = None
        self.scores = {P1: 0, P2: 0}
        self.ai_loop_id = None
        self.ai_delay = 400
        self.training = False
        self._stop_training = False

        self._build_ui()
        self.render()
        self.log("Welcome to Morabaraba!", "important")
        self.log("Train the AI first, then play against it.")

    # ─────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ─────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=WOOD_DARK)
        hdr.pack(fill="x")
        tk.Label(hdr, text="MORABARABA", font=("Georgia", 22, "bold"),
                 bg=WOOD_DARK, fg=GOLD_LIGHT).pack(pady=(10, 2))
        tk.Label(hdr, text="Southern African Strategy Game  —  Q-Learning Agent",
                 font=("Georgia", 10, "italic"), bg=WOOD_DARK, fg=TEXT_MUTED).pack(pady=(0, 8))

        # Main row
        main = tk.Frame(self, bg=BG_DARK)
        main.pack(padx=16, pady=12)

        self._build_left_panel(main)
        self._build_board(main)
        self._build_right_panel(main)

    def _card(self, parent, title=None):
        outer = tk.Frame(parent, bg=WOOD_MID, bd=1, relief="flat")
        outer.pack(fill="x", pady=4)
        inner = tk.Frame(outer, bg=PANEL_BG, padx=12, pady=10)
        inner.pack(fill="x", padx=1, pady=1)
        if title:
            tk.Label(inner, text=title.upper(), font=("Georgia", 7, "bold"),
                     bg=PANEL_BG, fg=GOLD).pack(anchor="w")
            tk.Frame(inner, bg=WOOD_MID, height=1).pack(fill="x", pady=(2, 6))
        return inner

    def _lbl(self, parent, text, **kw):
        kw.setdefault("bg", PANEL_BG)
        kw.setdefault("fg", CREAM)
        kw.setdefault("font", ("Georgia", 9))
        kw.setdefault("anchor", "w")
        return tk.Label(parent, text=text, **kw)

    def _stat_row(self, parent, label, var):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, bg=PANEL_BG, fg=TEXT_MUTED, font=("Georgia", 9)).pack(side="left")
        tk.Label(row, textvariable=var, bg=PANEL_BG, fg=CREAM, font=("Georgia", 9)).pack(side="right")

    def _btn(self, parent, text, cmd, style="normal"):
        colors = {
            "normal":  (PANEL_BG, CREAM,     WOOD_LIGHT),
            "primary": (WOOD_MID, GOLD_LIGHT, GOLD_LIGHT),
            "danger":  (PANEL_BG, "#d08080",  "#8b4040"),
            "active":  (WOOD_MID, GOLD_LIGHT, GOLD),
        }
        bg, fg, bdr = colors.get(style, colors["normal"])
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg, activebackground=WOOD_LIGHT,
                      font=("Georgia", 8, "bold"), relief="flat",
                      bd=1, highlightbackground=bdr, highlightthickness=1,
                      cursor="hand2", padx=8, pady=6)
        b.pack(fill="x", pady=2)
        return b

    def _build_left_panel(self, parent):
        panel = tk.Frame(parent, bg=BG_DARK, width=200)
        panel.pack(side="left", fill="y", padx=(0, 12))
        panel.pack_propagate(False)

        # Player 1 card
        c = self._card(panel, "Player 1")
        self.p1name_var = tk.StringVar(value="You (●)")
        tk.Label(c, textvariable=self.p1name_var, bg=PANEL_BG, fg=P1_BORDER,
                 font=("Georgia", 11, "bold")).pack(anchor="w")
        self.cow_canvas1 = tk.Canvas(c, bg=PANEL_BG, height=24, highlightthickness=0)
        self.cow_canvas1.pack(fill="x", pady=4)
        self.p1board_var = tk.StringVar(value="0")
        self.p1hand_var  = tk.StringVar(value="12")
        self.p1mills_var = tk.StringVar(value="0")
        self._stat_row(c, "On board", self.p1board_var)
        self._stat_row(c, "In hand",  self.p1hand_var)
        self._stat_row(c, "Mills",    self.p1mills_var)

        # Mode
        c = self._card(panel, "Game Mode")
        self.btn_human = self._btn(c, "⚔  Human vs AI", lambda: self.set_mode("human"), "active")
        self.btn_aivsai = self._btn(c, "🤖  AI vs AI",  lambda: self.set_mode("aivsai"))

        # AI speed (hidden until AI vs AI)
        self.speed_card_frame = tk.Frame(panel, bg=BG_DARK)
        sc = self._card(self.speed_card_frame, "AI Speed")
        self.speed_var = tk.IntVar(value=400)
        sl = tk.Scale(sc, from_=50, to=1000, orient="horizontal", variable=self.speed_var,
                      bg=PANEL_BG, fg=CREAM, troughcolor=WOOD_DARK, highlightthickness=0,
                      command=lambda v: setattr(self, "ai_delay", int(v)))
        sl.pack(fill="x")

        # Training
        c = self._card(panel, "AI Training")
        self.eps_var   = tk.StringVar(value="0")
        self.wr_var    = tk.StringVar(value="—")
        self.qst_var   = tk.StringVar(value="0")
        self.eps_e_var = tk.StringVar(value="1.000")
        self._stat_row(c, "Episodes", self.eps_var)
        self._stat_row(c, "Win rate", self.wr_var)
        self._stat_row(c, "Q-states", self.qst_var)
        self._stat_row(c, "Epsilon ε",self.eps_e_var)

        self.train_bar_var = tk.DoubleVar(value=0)
        pb = ttk.Progressbar(c, variable=self.train_bar_var, maximum=100, length=170)
        pb.pack(fill="x", pady=4)

        self.btn_train = self._btn(c, "▶  Train 500 eps",  lambda: self.start_training(500), "primary")
        self.btn_train5k = self._btn(c, "▶▶  Train 5000 eps", lambda: self.start_training(5000))

        tk.Frame(c, bg=WOOD_MID, height=1).pack(fill="x", pady=6)
        tk.Label(c, text="SAVE / LOAD BRAIN", bg=PANEL_BG, fg=GOLD,
                 font=("Georgia", 7, "bold")).pack(anchor="w")
        self._btn(c, "⬇  Export brain.json", self.export_brain)
        self._btn(c, "⬆  Import brain.json", self.import_brain)
        self.save_status_var = tk.StringVar(value="—")
        tk.Label(c, textvariable=self.save_status_var, bg=PANEL_BG, fg=TEXT_MUTED,
                 font=("Georgia", 8), wraplength=170).pack(anchor="w", pady=(2,0))

    def _build_board(self, parent):
        mid = tk.Frame(parent, bg=BG_DARK)
        mid.pack(side="left")

        self.canvas = tk.Canvas(mid, width=W, height=H, bg=BG_DARK,
                                highlightthickness=2, highlightbackground=WOOD_MID,
                                cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)

        self.status_var = tk.StringVar(value="Select a mode and place your first cow.")
        tk.Label(mid, textvariable=self.status_var, bg=PANEL_BG, fg=GOLD_LIGHT,
                 font=("Georgia", 10), wraplength=W-20, justify="center",
                 relief="flat", bd=0, padx=10, pady=8).pack(fill="x", pady=(6,0))

    def _build_right_panel(self, parent):
        panel = tk.Frame(parent, bg=BG_DARK, width=200)
        panel.pack(side="left", fill="y", padx=(12, 0))
        panel.pack_propagate(False)

        # Player 2 card
        c = self._card(panel, "Player 2")
        self.p2name_var = tk.StringVar(value="AI (○)")
        tk.Label(c, textvariable=self.p2name_var, bg=PANEL_BG, fg=P2_BORDER,
                 font=("Georgia", 11, "bold")).pack(anchor="w")
        self.cow_canvas2 = tk.Canvas(c, bg=PANEL_BG, height=24, highlightthickness=0)
        self.cow_canvas2.pack(fill="x", pady=4)
        self.p2board_var = tk.StringVar(value="0")
        self.p2hand_var  = tk.StringVar(value="12")
        self.p2mills_var = tk.StringVar(value="0")
        self._stat_row(c, "On board", self.p2board_var)
        self._stat_row(c, "In hand",  self.p2hand_var)
        self._stat_row(c, "Mills",    self.p2mills_var)

        # Phase card
        c = self._card(panel, "Game Phase")
        self.phase_var = tk.StringVar(value="Placing")
        self.phase_lbl = tk.Label(c, textvariable=self.phase_var,
                                  bg="#1a2a50", fg="#8ab0ff",
                                  font=("Georgia", 9, "bold"), padx=10, pady=4, relief="flat")
        self.phase_lbl.pack(anchor="center", pady=(0,4))
        self.move_num_var = tk.StringVar(value="0")
        self.score1_var   = tk.StringVar(value="0")
        self.score2_var   = tk.StringVar(value="0")
        self._stat_row(c, "Move #",  self.move_num_var)
        self._stat_row(c, "Score P1", self.score1_var)
        self._stat_row(c, "Score P2", self.score2_var)

        # Controls
        c = self._card(panel, "Controls")
        self._btn(c, "New Game",       self.new_game, "primary")
        self._btn(c, "Reset Everything", self.reset_all, "danger")

        # Log
        c = self._card(panel, "Move Log")
        self.log_text = tk.Text(c, width=22, height=16, bg=PANEL_BG, fg=TEXT_MUTED,
                                font=("Courier", 8), state="disabled",
                                relief="flat", highlightthickness=0, wrap="word")
        sb = tk.Scrollbar(c, command=self.log_text.yview, bg=WOOD_DARK)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.log_text.tag_config("important", foreground=GOLD_LIGHT)
        self.log_text.tag_config("warn",      foreground="#e07070")

    # ─────────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────────

    def log(self, msg, cls=""):
        self.log_text.configure(state="normal")
        tag = cls if cls else None
        self.log_text.insert("1.0", msg + "\n", tag)
        # Trim to ~80 lines
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 80:
            self.log_text.delete(f"{80}.0", "end")
        self.log_text.configure(state="disabled")

    # ─────────────────────────────────────────────────
    # RENDERING
    # ─────────────────────────────────────────────────

    def render(self):
        game = self.game
        # Highlights
        hl_set = set()
        shoot_set = set()
        if self.selected is not None:
            legal = game.get_legal_moves()
            hl_set = {m["to"] for m in legal if m["t"] == "move" and m["from"] == self.selected}
        if game.must_shoot:
            shoot_set = {m["pos"] for m in game.get_legal_moves()}

        mill_pos = set()
        for pl in [P1, P2]:
            for mill in MILLS:
                if all(game.board[i] == pl for i in mill):
                    mill_pos.update(mill)

        self._draw_board(game, self.selected, hl_set, shoot_set, mill_pos)
        self._update_stats()

    def _draw_board(self, game, selected, highlights, shoot_targets, mill_positions):
        c = self.canvas
        c.delete("all")

        # Background
        c.create_rectangle(0, 0, W, H, fill="#3d2008", outline="")
        c.create_oval(CX-280, CY-280, CX+280, CY+280,
                      fill="#1e0c04", outline="")

        # Mill highlights
        for mill in MILLS:
            if all(i in mill_positions for i in mill):
                pts = []
                for i in mill:
                    pts.extend(POS[i])
                c.create_line(*pts, fill=GOLD_LIGHT, width=10, capstyle="round", joinstyle="round")

        # Board lines
        edge_pairs = [
            (0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,0),
            (8,9),(9,10),(10,11),(11,12),(12,13),(13,14),(14,15),(15,8),
            (16,17),(17,18),(18,19),(19,20),(20,21),(21,22),(22,23),(23,16),
        ]
        spoke_pairs = [(1,9),(9,17),(3,11),(11,19),(5,13),(13,21),(7,15),(15,23)]
        diag_pairs  = [(0,8),(8,16),(2,10),(10,18),(4,12),(12,20),(6,14),(14,22)]

        for a, b in edge_pairs + spoke_pairs:
            c.create_line(*POS[a], *POS[b], fill=LINE_COL, width=2, capstyle="round")
        for a, b in diag_pairs:
            c.create_line(*POS[a], *POS[b], fill=LINE_DIAG, width=2, capstyle="round")

        # Nodes
        for i in range(24):
            x, y = POS[i]
            val = game.board[i]
            is_sel   = (selected == i)
            is_hl    = (i in highlights)
            is_shoot = (i in shoot_targets)

            # Highlight ring
            if is_hl or is_shoot:
                col      = "#c05050" if is_shoot else "#b0b030"
                fill_col = "#7a2020" if is_shoot else "#707020"
                c.create_oval(x-22, y-22, x+22, y+22,
                              fill=fill_col, outline=col, width=1.5, stipple="gray25")

            if val == EMPTY:
                c.create_oval(x-5, y-5, x+5, y+5, fill="#3a1a06", outline="#6a3a14", width=1.5)
            else:
                r = 18
                base   = P1_BASE   if val == P1 else P2_BASE
                border = P1_BORDER if val == P1 else P2_BORDER
                shine  = "#5a5aae" if val == P1 else "#d05050"
                lbl    = "●" if val == P1 else "○"

                if is_sel:
                    c.create_oval(x-r-4, y-r-4, x+r+4, y+r+4,
                                  fill="", outline=border, width=3)
                c.create_oval(x-r, y-r, x+r, y+r, fill=base, outline=border, width=2)
                # Shine
                c.create_oval(x-r*0.55-2, y-r*0.55-2, x-r*0.55+4, y-r*0.55+4,
                               fill="white", outline="", stipple="gray50")
                c.create_text(x, y+1, text=lbl, fill="white",
                              font=("Georgia", 12, "bold"))

        # Centre decoration
        c.create_oval(CX-28, CY-28, CX+28, CY+28, outline=GOLD, width=1, dash=(4,6))

    def _update_stats(self):
        g = self.game
        self.p1board_var.set(str(g.count_cows(P1)))
        self.p1hand_var.set(str(g.hand[P1]))
        self.p1mills_var.set(str(len(g.active_mills(P1))))
        self.p2board_var.set(str(g.count_cows(P2)))
        self.p2hand_var.set(str(g.hand[P2]))
        self.p2mills_var.set(str(len(g.active_mills(P2))))
        self.move_num_var.set(str(g.move_count))
        self.score1_var.set(str(self.scores[P1]))
        self.score2_var.set(str(self.scores[P2]))
        self._draw_cow_pips(self.cow_canvas1, P1, g.hand[P1], g.count_cows(P1))
        self._draw_cow_pips(self.cow_canvas2, P2, g.hand[P2], g.count_cows(P2))
        self._update_phase_badge()
        self._update_status()
        if g.phase == PHASE_OVER:
            self._show_win()

    def _draw_cow_pips(self, cv, player, in_hand, on_board):
        cv.delete("all")
        alive = in_hand + on_board
        col = P1_BORDER if player == P1 else P2_BORDER
        dim = "#333355"  if player == P1 else "#553333"
        for i in range(12):
            x = 8 + i * 15
            fill = col if i < alive else dim
            cv.create_oval(x, 4, x+10, 14, fill=fill, outline="")

    def _update_phase_badge(self):
        g = self.game
        if g.must_shoot:
            self.phase_var.set("Shooting!")
            self.phase_lbl.config(bg="#3a1010", fg="#ff8080")
        elif g.phase == PHASE_PLACING:
            self.phase_var.set("Placing")
            self.phase_lbl.config(bg="#1a2a50", fg="#8ab0ff")
        elif g.count_cows(g.current) <= 3 and g.phase == PHASE_MOVING:
            self.phase_var.set("Flying!")
            self.phase_lbl.config(bg="#2a2010", fg="#ffcc50")
        else:
            self.phase_var.set("Moving")
            self.phase_lbl.config(bg="#1a3020", fg="#80d080")

    def _update_status(self):
        g = self.game
        if g.phase == PHASE_OVER:
            self.status_var.set("Game Over!")
            return
        p = g.current
        sym = "●" if p == P1 else "○"
        is_human = self.mode == "human" and p == P1
        if g.must_shoot:
            self.status_var.set(f"{sym} formed a mill!  Click an opponent's cow to remove it.")
        elif g.phase == PHASE_PLACING:
            if is_human:
                self.status_var.set(f"Your turn (●) — Click an empty node to place a cow.  ({g.hand[P1]} remaining)")
            else:
                self.status_var.set(f"{sym}'s turn — Placing a cow.")
        else:
            if is_human:
                if self.selected is not None:
                    self.status_var.set(f"Cow at {self.selected} selected — click a highlighted node to move.")
                else:
                    self.status_var.set("Your turn (●) — Click one of your cows to select it.")
            else:
                self.status_var.set(f"{sym}'s turn — Moving a cow.")

    def _show_win(self):
        w = self.game.winner
        if w == P1:
            title = "You Win! 🎉" if self.mode == "human" else "AI-1 Wins!"
            msg = "Player 1 claims victory"
            self.scores[P1] += 1
        elif w == P2:
            title = "AI Wins! 🤖" if self.mode == "human" else "AI-2 Wins!"
            msg = "Player 2 claims victory"
            self.scores[P2] += 1
        else:
            title, msg = "Draw!", "A hard-fought draw"
        lbl = f"Player {1 if w == P1 else 2} wins" if w else "Draw"
        self.log(lbl, "important")
        self.after(800, lambda: self._win_dialog(title, msg))

    def _win_dialog(self, title, msg):
        dlg = tk.Toplevel(self)
        dlg.title("Game Over")
        dlg.configure(bg=PANEL_BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        tk.Label(dlg, text=title, font=("Georgia", 18, "bold"),
                 bg=PANEL_BG, fg=GOLD_LIGHT).pack(padx=50, pady=(30, 6))
        tk.Label(dlg, text=msg, font=("Georgia", 11, "italic"),
                 bg=PANEL_BG, fg=TEXT_MUTED).pack(pady=(0, 20))
        tk.Button(dlg, text="Play Again", command=lambda: (dlg.destroy(), self.new_game()),
                  bg=WOOD_MID, fg=GOLD_LIGHT, font=("Georgia", 10, "bold"),
                  relief="flat", padx=20, pady=8, cursor="hand2").pack(pady=(0, 30))

    # ─────────────────────────────────────────────────
    # CLICK HANDLING
    # ─────────────────────────────────────────────────

    def _on_click(self, event):
        if self.mode != "human" or self.game.phase == PHASE_OVER:
            return
        if self.game.current == P2:
            return
        # Find nearest node
        nearest, near_dist = -1, 9999
        for i, (nx, ny) in enumerate(POS):
            d = math.hypot(nx - event.x, ny - event.y)
            if d < near_dist:
                near_dist = d
                nearest = i
        if near_dist > 30:
            return
        self._handle_human_click(nearest)

    def _handle_human_click(self, pos):
        legal = self.game.get_legal_moves()
        if self.game.must_shoot:
            move = next((m for m in legal if m["t"] == "shoot" and m["pos"] == pos), None)
            if move:
                self.game.apply(move)
                self.log(f"You shoot pos {pos}")
                self.selected = None
                self.render()
                self._schedule_ai()
            return
        if self.game.phase == PHASE_PLACING:
            move = next((m for m in legal if m["t"] == "place" and m["pos"] == pos), None)
            if move:
                self.game.apply(move)
                self.log(f"You place at {pos}")
                self.selected = None
                self.render()
                self._schedule_ai()
            return
        if self.game.board[pos] == P1:
            self.selected = pos
            self.render()
            return
        if self.selected is not None:
            move = next((m for m in legal if m["t"] == "move" and m["from"] == self.selected and m["to"] == pos), None)
            if move:
                self.game.apply(move)
                self.log(f"You move {self.selected}→{pos}")
                self.selected = None
                self.render()
                self._schedule_ai()
                return
        self.selected = None
        self.render()

    def _schedule_ai(self):
        if self.mode == "human" and self.game.current == P2 and self.game.phase != PHASE_OVER:
            self.after(350, self._do_ai_move)

    def _do_ai_move(self):
        if self.game.phase == PHASE_OVER or self.game.current != P2:
            return
        move = self.agent2.choose(self.game, training=False)
        if not move:
            return
        if move["t"] == "shoot":
            desc = f"AI shoots {move['pos']}"
        elif move["t"] == "place":
            desc = f"AI places at {move['pos']}"
        else:
            desc = f"AI moves {move['from']}→{move['to']}"
        self.log(desc)
        self.game.apply(move)
        self.render()
        if self.game.must_shoot and self.game.current == P2:
            self.after(350, self._do_ai_move)

    # ─────────────────────────────────────────────────
    # AI vs AI LOOP
    # ─────────────────────────────────────────────────

    def _start_ai_loop(self):
        self._stop_ai_loop()
        def step():
            if self.game.phase == PHASE_OVER:
                self.after(1500, self.new_game)
                return
            agent = self.agent1 if self.game.current == P1 else self.agent2
            move = agent.choose(self.game, training=False)
            if not move:
                self.game.phase = PHASE_OVER
                self.render()
                return
            self.game.apply(move)
            self.render()
            self.ai_loop_id = self.after(self.ai_delay, step)
        self.ai_loop_id = self.after(self.ai_delay, step)

    def _stop_ai_loop(self):
        if self.ai_loop_id:
            self.after_cancel(self.ai_loop_id)
            self.ai_loop_id = None

    # ─────────────────────────────────────────────────
    # MODE / GAME CONTROLS
    # ─────────────────────────────────────────────────

    def set_mode(self, m):
        self.mode = m
        self.btn_human.config(bg=WOOD_MID  if m=="human"  else PANEL_BG,
                              fg=GOLD_LIGHT if m=="human" else CREAM)
        self.btn_aivsai.config(bg=WOOD_MID  if m=="aivsai" else PANEL_BG,
                               fg=GOLD_LIGHT if m=="aivsai" else CREAM)
        if m == "human":
            self.p1name_var.set("You (●)")
            self.p2name_var.set("AI (○)")
            self.speed_card_frame.pack_forget()
            self._stop_ai_loop()
        else:
            self.p1name_var.set("AI-1 (●)")
            self.p2name_var.set("AI-2 (○)")
            self.speed_card_frame.pack(fill="x", pady=4)
        self.new_game()

    def new_game(self):
        self._stop_ai_loop()
        self.game = Game()
        self.selected = None
        self.log("New game started", "important")
        self.render()
        if self.mode == "aivsai":
            self._start_ai_loop()

    def reset_all(self):
        if not messagebox.askyesno("Reset Everything",
                                   "Reset all training data and scores?"):
            return
        self._stop_ai_loop()
        self.agent1 = QAgent(P1)
        self.agent2 = QAgent(P2)
        self.scores = {P1: 0, P2: 0}
        self.game = Game()
        self.selected = None
        self.log("Everything reset.", "warn")
        self._update_train_stats()
        self.render()

    # ─────────────────────────────────────────────────
    # TRAINING
    # ─────────────────────────────────────────────────

    def _update_train_stats(self):
        a = self.agent1
        self.eps_var.set(f"{a.episodes:,}")
        self.wr_var.set(f"{a.win_rate:.1%}" if a.episodes else "—")
        self.qst_var.set(f"{a.q_size:,}")
        self.eps_e_var.set(f"{a.epsilon:.3f}")

    def start_training(self, total=500):
        if self.training:
            return
        self.training = True
        self._stop_training = False
        self.btn_train.config(text="Training…")
        self.btn_train5k.config(text="Training…")
        t0 = time.time()
        chunk = 50
        done = [0]

        def do_chunk():
            if self._stop_training:
                self._finish_training(total, t0)
                return
            end = min(done[0] + chunk, total)
            for _ in range(done[0], end):
                self_play_episode(self.agent1, self.agent2)
            done[0] = end
            self.train_bar_var.set(done[0] / total * 100)
            self._update_train_stats()
            if done[0] < total:
                self.after(0, do_chunk)
            else:
                self._finish_training(total, t0)

        self.after(0, do_chunk)

    def _finish_training(self, total, t0):
        self.training = False
        elapsed = time.time() - t0
        self.train_bar_var.set(0)
        self.btn_train.config(text="▶  Train 500 eps")
        self.btn_train5k.config(text="▶▶  Train 5000 eps")
        self.log(f"Trained {total} eps in {elapsed:.1f}s. Q-states: {self.agent1.q_size:,}", "important")
        self.save_status_var.set(f"Trained — {self.agent1.episodes:,} eps")

    # ─────────────────────────────────────────────────
    # BRAIN SAVE / LOAD
    # ─────────────────────────────────────────────────

    def export_brain(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"morabaraba_brain_{self.agent1.episodes}eps.json"
        )
        if not path:
            return
        data = {"version": 1, "agent1": self.agent1.to_dict(), "agent2": self.agent2.to_dict()}
        with open(path, "w") as f:
            json.dump(data, f)
        self.save_status_var.set(f"Exported — {self.agent1.episodes:,} eps")
        self.log("Brain exported.", "important")

    def import_brain(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get("version") != 1:
                raise ValueError("Invalid version")
            self.agent1.from_dict(data["agent1"])
            self.agent2.from_dict(data["agent2"])
            self._update_train_stats()
            self.save_status_var.set(f"Loaded — {self.agent1.episodes:,} eps")
            self.log(f"Brain loaded: {self.agent1.episodes:,} eps, {self.agent1.q_size:,} Q-states", "important")
        except Exception as e:
            messagebox.showerror("Import failed", str(e))


# ═══════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    app = MorabarabaApp()
    app.mainloop()