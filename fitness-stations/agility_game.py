"""Agility Tracker: touch the green targets with your hands, avoid the red ones.

Stand 1.5-2.5 m from the camera, facing it, with your upper body and arm reach in frame.
The screen is mirrored, so move like you're looking in a mirror.

Scoring
  Green target   +10   (hit it before its ring runs out)
  Red target     -5    (touching it also breaks your streak)
  Missed green         breaks your streak
  5 greens in a row    +25 bonus (every 5 in an unbroken streak)

Targets disappear faster as the game goes on.

Controls
  + / -   change the time limit (setup screen)
  SPACE   start
  R       play again (results screen)
  Q / ESC quit
"""
import argparse
import random
import time
from dataclasses import dataclass

import cv2

from pose_utils import (
    GREEN, RED, YELLOW, WHITE,
    L_ELBOW, R_ELBOW, L_WRIST, R_WRIST,
    PoseTracker, center_text, open_camera, text, visible,
)

GOOD_POINTS = 10
BAD_POINTS = -5
STREAK_FOR_BONUS = 5
BONUS_POINTS = 25
BAD_CHANCE = 0.3          # fraction of targets that are red
MAX_TARGETS = 3           # targets on screen at once
SPAWN_GAP = (0.4, 0.9)    # seconds between new targets (min, max)
LIFETIME_START = 2.5      # seconds a target stays at the start of the game...
LIFETIME_END = 1.2        # ...shrinking to this by the end
RADIUS = 0.06             # target radius as a fraction of frame height
HAND_REACH = 0.35         # hand point = wrist pushed this far along the forearm (wrist is short of the fingertips)
BLUE = (255, 160, 60)


@dataclass
class Target:
    x: int
    y: int
    r: int
    good: bool
    born: float
    life: float

    def remaining(self, now):
        return 1.0 - (now - self.born) / self.life


@dataclass
class Popup:
    msg: str
    x: int
    y: int
    color: tuple
    born: float


def hand_points(kpts):
    """Approximate hand positions: the wrist pushed a bit further along the forearm."""
    hands = []
    for elbow, wrist in ((L_ELBOW, L_WRIST), (R_ELBOW, R_WRIST)):
        if visible(kpts, wrist):
            wx, wy = kpts[wrist][0], kpts[wrist][1]
            if visible(kpts, elbow):
                wx += (wx - kpts[elbow][0]) * HAND_REACH
                wy += (wy - kpts[elbow][1]) * HAND_REACH
            hands.append((int(wx), int(wy)))
    return hands


class Game:
    def __init__(self, limit, w, h):
        self.limit, self.w, self.h = limit, w, h
        self.score = self.streak = self.best_streak = 0
        self.hits = self.misses = self.bad_hits = self.bonuses = 0
        self.reactions = []
        self.targets, self.popups = [], []
        self.start = self.next_spawn = 0.0

    def begin(self, now):
        self.start = self.next_spawn = now

    def time_left(self, now):
        return self.limit - (now - self.start)

    def _spawn(self, now):
        r = int(self.h * RADIUS)
        progress = min(1.0, (now - self.start) / self.limit)
        life = LIFETIME_START + (LIFETIME_END - LIFETIME_START) * progress
        # Keep targets within arm's reach: avoid the edges and the bottom of the frame
        for _ in range(20):
            x = random.randint(int(self.w * 0.12), int(self.w * 0.88))
            y = random.randint(int(self.h * 0.12), int(self.h * 0.70))
            if all((x - t.x) ** 2 + (y - t.y) ** 2 > (3 * r) ** 2 for t in self.targets):
                break
        self.targets.append(Target(x, y, r, random.random() > BAD_CHANCE, now, life))

    def _popup(self, msg, x, y, color, now):
        self.popups.append(Popup(msg, x, y, color, now))

    def update(self, hands, now):
        if now >= self.next_spawn and len(self.targets) < MAX_TARGETS:
            self._spawn(now)
            self.next_spawn = now + random.uniform(*SPAWN_GAP)

        for t in list(self.targets):
            touched = any((hx - t.x) ** 2 + (hy - t.y) ** 2 <= (t.r * 1.15) ** 2 for hx, hy in hands)
            if touched:
                self.targets.remove(t)
                if t.good:
                    self.hits += 1
                    self.streak += 1
                    self.best_streak = max(self.best_streak, self.streak)
                    self.reactions.append(now - t.born)
                    self.score += GOOD_POINTS
                    self._popup(f"+{GOOD_POINTS}", t.x, t.y, GREEN, now)
                    if self.streak % STREAK_FOR_BONUS == 0:
                        self.bonuses += 1
                        self.score += BONUS_POINTS
                        self._popup(f"{STREAK_FOR_BONUS} IN A ROW! +{BONUS_POINTS}", t.x, t.y - 50, YELLOW, now)
                else:
                    self.bad_hits += 1
                    self.streak = 0
                    self.score += BAD_POINTS
                    self._popup(str(BAD_POINTS), t.x, t.y, RED, now)
            elif t.remaining(now) <= 0:
                self.targets.remove(t)
                if t.good:
                    self.misses += 1
                    self.streak = 0
                    self._popup("MISS", t.x, t.y, RED, now)

        self.popups = [p for p in self.popups if now - p.born < 0.8]

    def draw(self, img, hands, now):
        overlay = img.copy()
        for t in self.targets:
            color = GREEN if t.good else RED
            cv2.circle(overlay, (t.x, t.y), t.r, color, -1)
        cv2.addWeighted(overlay, 0.45, img, 0.55, 0, img)
        for t in self.targets:
            color = GREEN if t.good else RED
            # ring shrinks as the target's time runs out
            sweep = int(360 * max(0.0, t.remaining(now)))
            cv2.ellipse(img, (t.x, t.y), (t.r + 6, t.r + 6), -90, 0, sweep, color, 5, cv2.LINE_AA)
            label = "+" if t.good else "X"
            text(img, label, (t.x - 14, t.y + 14), 1.4, WHITE, 3)
        for hx, hy in hands:
            cv2.circle(img, (hx, hy), 16, BLUE, -1, cv2.LINE_AA)
            cv2.circle(img, (hx, hy), 16, WHITE, 2, cv2.LINE_AA)
        for p in self.popups:
            rise = int((now - p.born) * 60)
            text(img, p.msg, (p.x - 30, p.y - rise), 1.1, p.color, 3)

        left = max(0.0, self.time_left(now))
        text(img, f"Score: {self.score}", (20, 55), 1.5, WHITE, 3)
        text(img, f"{left:04.1f}s", (self.w - 200, 55), 1.5, RED if left < 5 else WHITE, 3)
        # streak meter: one pip per green in the current run toward the next bonus
        text(img, "Streak", (20, 100), 0.8, YELLOW)
        pips = self.streak % STREAK_FOR_BONUS
        for i in range(STREAK_FOR_BONUS):
            c = (130 + i * 34, 100)
            cv2.circle(img, c, 10, YELLOW, -1 if i < pips else 2, cv2.LINE_AA)
        text(img, f"x{self.streak}", (130 + STREAK_FOR_BONUS * 34, 108), 0.8, YELLOW)
        cv2.rectangle(img, (0, self.h - 8), (int(self.w * left / self.limit), self.h), YELLOW, -1)

    def draw_results(self, img, best):
        h = self.h
        avg = sum(self.reactions) / len(self.reactions) if self.reactions else 0
        total = self.hits + self.misses
        acc = 100 * self.hits / total if total else 0
        center_text(img, "TIME'S UP!", 90, 2.0, YELLOW, 4)
        center_text(img, f"Score: {self.score}", 170, 1.8, GREEN, 4)
        lines = [
            f"Greens hit: {self.hits}/{total}  ({acc:.0f}%)",
            f"Reds touched: {self.bad_hits}",
            f"Best streak: {self.best_streak}   Bonuses: {self.bonuses}",
            f"Avg reaction: {avg:.2f}s" if self.reactions else "Avg reaction: -",
            f"High score: {best}",
        ]
        for i, line in enumerate(lines):
            center_text(img, line, 240 + i * 45, 1.0, WHITE, 2)
        center_text(img, "R  play again     Q  quit", h - 40, 0.9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=int, default=60, help="starting time limit in seconds")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--model", default="yolo11n-pose.pt")
    args = ap.parse_args()

    tracker = PoseTracker(args.model)
    cap = open_camera(args.camera)
    win = "Agility Tracker"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    limit, state, best, game, t0 = args.time, "setup", 0, None, 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        kpts, _, img = tracker.track(frame)
        h, w = img.shape[:2]
        now = time.time()
        hands = hand_points(kpts) if kpts is not None else []

        if state == "setup":
            center_text(img, "AGILITY TRACKER", 90, 1.6, YELLOW)
            center_text(img, f"Time limit: {limit}s", h // 2 - 20, 2.0)
            center_text(img, f"Hit GREEN +{GOOD_POINTS}   Avoid RED {BAD_POINTS}   "
                             f"{STREAK_FOR_BONUS} in a row = +{BONUS_POINTS}", h // 2 + 40, 0.8, WHITE, 2)
            msg, col = (f"{len(hands)} hand(s) detected", GREEN) if hands else ("Raise your hands into view", RED)
            center_text(img, msg, h // 2 + 90, 0.9, col, 2)
            center_text(img, "+ / -  change time     SPACE  start     Q  quit", h - 40, 0.8)
            for hx, hy in hands:
                cv2.circle(img, (hx, hy), 16, BLUE, -1, cv2.LINE_AA)

        elif state == "countdown":
            remaining = 3 - int(now - t0)
            if remaining <= 0:
                game = Game(limit, w, h)
                game.begin(now)
                state = "play"
            else:
                center_text(img, "Get ready!", 90, 1.4, YELLOW)
                center_text(img, str(remaining), h // 2 + 40, 5.0, YELLOW, 8)

        elif state == "play":
            if game.time_left(now) <= 0:
                best = max(best, game.score)
                state = "results"
            else:
                game.update(hands, now)
                game.draw(img, hands, now)

        if state == "results":
            game.draw_results(img, best)

        cv2.imshow(win, img)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if state == "setup":
            if key in (ord("+"), ord("=")):
                limit = min(300, limit + 15)
            elif key in (ord("-"), ord("_")):
                limit = max(15, limit - 15)
            elif key == ord(" "):
                state, t0 = "countdown", now
        elif state == "results" and key == ord("r"):
            state = "setup"

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
