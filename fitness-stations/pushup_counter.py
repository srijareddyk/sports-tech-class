import argparse
import math
import time

import cv2

from pose_utils import (
    GREEN, RED, YELLOW, WHITE,
    L_SHOULDER, R_SHOULDER, L_ELBOW, R_ELBOW, L_WRIST, R_WRIST, L_HIP, R_HIP,
    PoseTracker, angle, center_text, open_camera, text, visible,
)

DOWN_ANGLE = 95    # elbow angle (deg) that counts as the bottom of a push-up
UP_ANGLE = 155     # elbow angle (deg) that counts as arms locked out
MAX_TORSO_TILT = 50  # shoulder->hip line must be within this many degrees of horizontal
SMOOTHING = 0.5    # 0 = no smoothing, closer to 1 = smoother but laggier


def elbow_angle(kpts):
    """Elbow angle from whichever arm the camera sees best, or None."""
    sides = [(L_SHOULDER, L_ELBOW, L_WRIST), (R_SHOULDER, R_ELBOW, R_WRIST)]
    sides = [s for s in sides if visible(kpts, *s)]
    if not sides:
        return None
    s, e, w = max(sides, key=lambda s: sum(kpts[i][2] for i in s))
    return angle(kpts[s], kpts[e], kpts[w])


def in_plank(kpts):
    """True when the torso is roughly horizontal (so standing arm curls don't count)."""
    for sh, hip in ((L_SHOULDER, L_HIP), (R_SHOULDER, R_HIP)):
        if visible(kpts, sh, hip):
            dx = kpts[hip][0] - kpts[sh][0]
            dy = kpts[hip][1] - kpts[sh][1]
            tilt = abs(math.degrees(math.atan2(dy, dx)))
            tilt = min(tilt, 180 - tilt)  # angle from horizontal
            return tilt <= MAX_TORSO_TILT
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--time", type=int, default=30, help="starting time limit in seconds")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--model", default="yolo11n-pose.pt")
    args = ap.parse_args()

    tracker = PoseTracker(args.model)
    cap = open_camera(args.camera)
    win = "Push-up Challenge"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    limit = args.time
    state = "setup"
    best = 0
    count, stage, smooth, t0 = 0, "up", None, 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        kpts, _, img = tracker.track(frame)
        h, w = img.shape[:2]
        now = time.time()

        if state == "setup":
            center_text(img, "PUSH-UP CHALLENGE", 90, 1.6, YELLOW)
            center_text(img, f"Time limit: {limit}s", h // 2, 2.0)
            center_text(img, "+ / -  change time     SPACE  start     Q  quit", h - 40, 0.8)
            if kpts is not None:
                center_text(img, "Player detected", h // 2 + 60, 0.9, GREEN, 2)
            else:
                center_text(img, "Step into view (side-on to camera)", h // 2 + 60, 0.9, RED, 2)

        elif state == "countdown":
            remaining = 3 - int(now - t0)
            if remaining <= 0:
                state, t0 = "play", now
                count, stage, smooth = 0, "up", None
            else:
                center_text(img, "Get in plank position!", 90, 1.2, YELLOW)
                center_text(img, str(remaining), h // 2 + 40, 5.0, YELLOW, 8)

        elif state == "play":
            left = limit - (now - t0)
            if left <= 0:
                best = max(best, count)
                state = "results"
            elif kpts is not None:
                a = elbow_angle(kpts)
                if a is not None:
                    smooth = a if smooth is None else SMOOTHING * smooth + (1 - SMOOTHING) * a
                    plank = in_plank(kpts)
                    if stage == "up" and smooth < DOWN_ANGLE and plank:
                        stage = "down"
                    elif stage == "down" and smooth > UP_ANGLE:
                        stage = "up"
                        count += 1
                    text(img, f"Elbow: {int(smooth)} deg", (20, h - 60), 0.8)
                    text(img, "Plank OK" if plank else "Straighten your body",
                         (20, h - 25), 0.8, GREEN if plank else RED)

            text(img, f"Push-ups: {count}", (20, 60), 1.6, GREEN, 3)
            timer = f"{max(0, left):04.1f}s"
            text(img, timer, (w - 220, 60), 1.6, RED if left < 5 else WHITE, 3)
            text(img, stage.upper(), (20, 110), 1.0, YELLOW)
            # progress bar for time remaining
            frac = max(0.0, left / limit)
            cv2.rectangle(img, (0, h - 8), (int(w * frac), h), YELLOW, -1)

        elif state == "results":
            center_text(img, "TIME'S UP!", 110, 2.0, YELLOW, 4)
            center_text(img, f"{count} push-ups in {limit}s", h // 2, 1.8, GREEN, 4)
            center_text(img, f"Best: {best}", h // 2 + 70, 1.2)
            center_text(img, "R  play again     Q  quit", h - 40, 0.9)

        cv2.imshow(win, img)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if state == "setup":
            if key in (ord("+"), ord("=")):
                limit = min(300, limit + 5)
            elif key in (ord("-"), ord("_")):
                limit = max(5, limit - 5)
            elif key == ord(" "):
                state, t0 = "countdown", now
        elif state == "results" and key == ord("r"):
            state = "setup"

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
