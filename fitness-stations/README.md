# Fitness Stations (YOLO pose)

Webcam stations built on the YOLO11 pose model (17 body keypoints per person).

| Station | File | What it does |
|---|---|---|
| Push-up Challenge | `pushup_counter.py` | Player sets a time limit, then the game counts push-ups until time runs out |
| Vertical Jump Meter | `jump_meter.py` | Measures how high the player jumps, in cm |
| Agility Tracker | `agility_game.py` | Touch green targets with your hands, avoid red ones, build streaks for bonuses |

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On macOS, allow camera access for your terminal when it asks.

## Push-up Challenge

```bash
.venv/bin/python pushup_counter.py --time 30
```

- Camera at floor level, **side-on** to the player, whole body in frame.
- `+`/`-` changes the time limit (5 s steps), `SPACE` starts a 3-2-1 countdown, `R` plays again.

**How a rep is counted:** the elbow angle (shoulder–elbow–wrist) is measured on whichever arm the
camera sees best. A rep counts when the elbow bends below 95° *while the body is in a plank*
(shoulder–hip line within 50° of horizontal) and then straightens past 155°. The plank check
stops standing arm bends from being counted. Thresholds are constants at the top of the file.

## Vertical Jump Meter

```bash
.venv/bin/python jump_meter.py --height 170
```

- Camera 3–4 m away at hip height, **facing** the player, whole body plus space above the head in frame.
- Set the player's real height with `+`/`-` (or `--height`), press `SPACE`, stand still for 2 s.
- Jump straight up, in place. Each jump shows **Last**, **Best**, and the 5 most recent results.
- `C` recalibrates (do this for each new player), `R` resets.

**How height is measured:**
1. Calibration: the player's bounding-box height in pixels is matched to their real height,
   which gives cm per pixel. The standing hip and ankle positions are saved.
2. Takeoff: the ankles rise more than 3% of body height above the standing position.
3. While airborne, the highest hip position is tracked.
4. Landing: the ankles return to the floor. Jump height = (standing hip − highest hip) × cm per pixel.

Using the hips (close to the centre of mass) instead of the feet means tucking the knees doesn't
inflate the score. Accuracy depends on the player staying the same distance from the camera.

## Agility Tracker

```bash
.venv/bin/python agility_game.py --time 60
```

- Stand 1.5–2.5 m from the camera, facing it, with your arm reach in frame. The view is mirrored.
- `+`/`-` changes the time limit (15 s steps), `SPACE` starts, `R` plays again.

| Event | Points | Streak |
|---|---|---|
| Touch a green target | +10 | +1 |
| Every 5 greens in a row | +25 bonus | continues |
| Touch a red target | −5 | resets |
| A green target runs out | 0 | resets |

Up to 3 targets are on screen at once (about 30% are red). Each target's ring shows how long it
has left; targets start at 2.5 s and speed up to 1.2 s by the end. The results screen shows score,
accuracy, red touches, best streak, bonuses and average reaction time.

Hands are tracked from the wrist keypoints, nudged forward along the forearm to approximate the
palm. Tuning constants (points, speed, red chance, target size) are at the top of the file.

## Options

All scripts accept `--camera N` (default 0) and `--model` (for example `yolo11s-pose.pt` is
more accurate but slower).
