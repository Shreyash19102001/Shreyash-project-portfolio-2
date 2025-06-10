from flask import Flask, render_template_string
import cv2
import threading
import pygame.midi
import time
from cvzone.HandTrackingModule import HandDetector

app = Flask(__name__)

# Initialize Pygame MIDI
pygame.midi.init()
player = pygame.midi.Output(0)
player.set_instrument(0)

# Initialize Hand Detector
cap = cv2.VideoCapture(0)
detector = HandDetector(detectionCon=0.8)

chords = {
    "left": {
        "thumb": [62, 66, 69],
        "index": [64, 67, 71],
        "middle": [66, 69, 73],
        "ring": [67, 71, 74],
        "pinky": [69, 73, 76]
    },
    "right": {
        "thumb": [62, 66, 69],
        "index": [64, 67, 71],
        "middle": [66, 69, 73],
        "ring": [67, 71, 74],
        "pinky": [69, 73, 98]
    }
}

SUSTAIN_TIME = 2.0
prev_states = {hand: {finger: 0 for finger in chords[hand]} for hand in chords}
hand_tracking_running = False

def play_chord(chord_notes):
    for note in chord_notes:
        player.note_on(note, 127)

def stop_chord_after_delay(chord_notes):
    time.sleep(SUSTAIN_TIME)
    for note in chord_notes:
        player.note_off(note, 127)

def hand_tracking_loop():
    global hand_tracking_running
    hand_tracking_running = True

    while hand_tracking_running:
        success, img = cap.read()
        if not success:
            print("❌ Camera not capturing frames")
            continue

        hands, img = detector.findHands(img, draw=True)
        if hands:
            for hand in hands:
                hand_type = "left" if hand["type"] == "Left" else "right"
                fingers = detector.fingersUp(hand)
                finger_names = ["thumb", "index", "middle", "ring", "pinky"]

                for i, finger in enumerate(finger_names):
                    if finger in chords[hand_type]:
                        if fingers[i] == 1 and prev_states[hand_type][finger] == 0:
                            play_chord(chords[hand_type][finger])
                        elif fingers[i] == 0 and prev_states[hand_type][finger] == 1:
                            threading.Thread(target=stop_chord_after_delay, args=(chords[hand_type][finger],), daemon=True).start()
                        prev_states[hand_type][finger] = fingers[i]
        else:
            for hand in chords:
                for finger in chords[hand]:
                    threading.Thread(target=stop_chord_after_delay, args=(chords[hand][finger],), daemon=True).start()
            for hand in prev_states:
                for finger in prev_states[hand]:
                    prev_states[hand][finger] = 0

        cv2.imshow("Hand Tracking MIDI Chords (press q to exit)", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            hand_tracking_running = False
            break

    cap.release()
    cv2.destroyAllWindows()
    pygame.midi.quit()

# Serve the frontpage HTML directly
with open("forntpage.html", "r", encoding="utf-8") as f:
    html_content = f.read()

@app.route('/')
def home():
    return render_template_string(html_content)

@app.route('/start')
def start_tracking():
    threading.Thread(target=hand_tracking_loop, daemon=True).start()
    return "Hand Tracking Started"

if __name__ == '__main__':
    app.run(debug=True)
