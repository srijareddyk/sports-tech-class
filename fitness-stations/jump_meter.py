import argparse
import statistics
import time

import cv2

from pose_utils import (
    GREEN, RED, YELLOW,
    L_HIP, R_HIP, L_ANKLE, R_ANKLE,
    PoseTracker, center_text, open_camera, text, visible,
)

CALIBRATION_SECONDS = 2.0
TAKEOFF = 0.03    # feet must rise this fraction of body height to count as airborne
LANDED = 0.015    # feet back within this fraction of body height = landed
STILL_TOLERANCE = 0.05  # max change in body size (fraction) allowed while calibrating


def avg_y(kpts, a, b):
    """Average y of two keypoints, using whichever are visible."""
    ys = [kpts[i][1] for i in (a, b) if visible(kpts, i)]
    return sum(ys) / len(ys) if ys else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--height", type=int, default=170, help="player height in cm")
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--model", default="yolo11n-pose.pt")
    args = ap.parse_args()

    tracker = PoseTracker(args.model)
    cap = open_camera(args.camera)
    win = "Vertical Jump Meter"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    height_cm = args.height
    state = "setup"
    samples, t0 = [], 0.0
    body_px = cm_per_px = base_hip = base_ankle = None
    peak_hip = None
    last_jump, best, history = None, 0.0, []

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        kpts, box, img = tracker.track(frame)
        h, w = img.shape[:2]
        now = time.time()

        hip = ankle = None
        if kpts is not None:
            hip = avg_y(kpts, L_HIP, R_HIP)
            ankle = avg_y(kpts, L_ANKLE, R_ANKLE)
        full_body = hip is not None and ankle is not None and box is not None

        if state == "setup":
            center_text(img, "VERTICAL JUMP METER", 90, 1.6, YELLOW)
            center_text(img, f"Player height: {height_cm} cm", h // 2, 1.8)
            center_text(img, "+ / -  change height     SPACE  calibrate     Q  quit", h - 40, 0.8)
            msg, col = ("Full body detected", GREEN) if full_body else ("Step back so your whole body is visible", RED)
            center_text(img, msg, h // 2 + 60, 0.9, col, 2)

        elif state == "calibrate":
            center_text(img, "Stand still...", 90, 1.6, YELLOW)
            if full_body:
                samples.append((box[3] - box[1], hip, ankle))
                bodies = [s[0] for s in samples]
                # Restart if the player moves too much
                if max(bodies) - min(bodies) > STILL_TOLERANCE * statistics.median(bodies):
                    samples, t0 = [], now
            else:
                samples, t0 = [], now
            done = min(1.0, (now - t0) / CALIBRATION_SECONDS)
            cv2.rectangle(img, (w // 4, h // 2), (w // 4 + int(w / 2 * done), h // 2 + 30), GREEN, -1)
            cv2.rectangle(img, (w // 4, h // 2), (3 * w // 4, h // 2 + 30), (255, 255, 255), 2)
            if done >= 1.0 and len(samples) >= 5:
                body_px = statistics.median(s[0] for s in samples)
                base_hip = statistics.median(s[1] for s in samples)
                base_ankle = statistics.median(s[2] for s in samples)
                cm_per_px = height_cm / body_px
                state = "ready"

        elif state in ("ready", "air"):
            if full_body:
                feet_rise = (base_ankle - ankle) / body_px
                if state == "ready" and feet_rise > TAKEOFF:
                    state, peak_hip = "air", hip
                elif state == "air":
                    peak_hip = min(peak_hip, hip)  # smaller y = higher on screen
                    if feet_rise < LANDED:
                        last_jump = max(0.0, (base_hip - peak_hip) * cm_per_px)
                        best = max(best, last_jump)
                        history = (history + [last_jump])[-5:]
                        state = "ready"
                # standing reference line
                cv2.line(img, (0, int(base_hip)), (w, int(base_hip)), YELLOW, 1)

            status = "IN THE AIR!" if state == "air" else "JUMP!"
            center_text(img, status, 80, 1.8, GREEN if state == "air" else YELLOW, 4)
            if last_jump is not None:
                text(img, f"Last: {last_jump:.1f} cm", (20, h - 110), 1.4, GREEN, 3)
                text(img, f"Best: {best:.1f} cm", (20, h - 60), 1.2, YELLOW, 3)
            if history:
                text(img, "Recent: " + "  ".join(f"{j:.0f}" for j in history), (20, h - 20), 0.8)
            text(img, "C recalibrate   R reset   Q quit", (w - 470, h - 20), 0.7)
            if not full_body:
                center_text(img, "Can't see your whole body", 140, 0.9, RED, 2)

        cv2.imshow(win, img)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if state == "setup":
            if key in (ord("+"), ord("=")):
                height_cm = min(230, height_cm + 1)
            elif key in (ord("-"), ord("_")):
                height_cm = max(100, height_cm - 1)
            elif key == ord(" "):
                state, samples, t0 = "calibrate", [], now
        elif key == ord("c"):
            state, samples, t0 = "calibrate", [], now
        elif key == ord("r"):
            state, last_jump, best, history = "setup", None, 0.0, []

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
