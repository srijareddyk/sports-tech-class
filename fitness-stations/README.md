# Fitness Stations (YOLO pose)

Two webcam stations built on the YOLO11 pose model (17 body keypoints per person).

| Station | File | What it does |
|---|---|---|
| Push-up Challenge | `pushup_counter.py` | Player sets a time limit, then the game counts push-ups until time runs out |
| Vertical Jump Meter | `jump_meter.py` | Measures how high the player jumps, in cm |

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

## Options

Both scripts accept `--camera N` (default 0) and `--model` (for example `yolo11s-pose.pt` is
more accurate but slower).
