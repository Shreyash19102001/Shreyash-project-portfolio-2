from flask import Flask, render_template_string, send_file
import cv2
import threading
import pygame.midi
import time
import os  # Import os for file handling
from cvzone.HandTrackingModule import HandDetector

app = Flask(__name__)

# 🎹 Initialize MIDI
pygame.midi.init()
player = pygame.midi.Output(0)
player.set_instrument(0)

# 🎵 Instrument Mapping
instruments = {
    "guitar": {
        "left": {
            "thumb": [26, 86, 59],     # D Major
            "index": [68, 62, 41],     # E Minor
            "middle": [46, 29, 24],    # G Major
        },
        "right": {
            "thumb": [69, 73, 76],     # A Major
            "index": [71, 74, 78],     # B Minor
            "middle": [73, 76, 80]     # F# Minor
        }
    },
    "sitar": {
        "left": {
            "thumb": [60, 64, 67],     # C Major
            "index": [62, 65, 69],     # D Minor
            "middle": [64, 67, 71],    # E Major
        },
        "right": {
            "thumb": [65, 69, 72],     # F Major
            "index": [67, 70, 74],     # G Minor
            "middle": [69, 72, 76]     # A Major
        }
    },
    "drum": {
        "left": {
            "thumb": [36],              # Bass Drum
            "index": [38],              # Snare Drum
            "middle": [42],             # Hi-Hat
        },
        "right": {
            "thumb": [49],              # Crash Cymbal
            "index": [51],              # Ride Cymbal
            "middle": [53]              # Tom-Tom
        }
    }
}

SUSTAIN_TIME = 2.0
prev_states = {hand: {finger: 0 for finger in instruments["guitar"][hand]} for hand in ["left", "right"]}
hand_tracking_running = False
current_instrument = "guitar"  # Default instrument
recording = False  # Flag to indicate if recording is active

# 🔊 MIDI Functions
def play_chord(chord_notes):
    for note in chord_notes:
        player.note_on(note, 127)

def stop_chord_after_delay(chord_notes):
    time.sleep(SUSTAIN_TIME)
    for note in chord_notes:
        player.note_off(note, 127)

# 🖐️ Hand Tracking Logic
def hand_tracking_loop():
    global hand_tracking_running, recording
    print("🟡 Hand tracking thread started")

    cap = None
    for i in range(3):  # Try different webcam indexes
        temp_cap = cv2.VideoCapture(i)
        if temp_cap.isOpened():
            cap = temp_cap
            print(f"✅ Webcam successfully opened at index {i}")
            break
    else:
        print("❌ No working webcam found.")
        return

    # Video recording setup
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 20.0, (640, 480))  # Adjust resolution as needed

    detector = HandDetector(detectionCon=0.8)
    hand_tracking_running = True

    try:
        while hand_tracking_running:
            success, img = cap.read()
            if not success or img is None:
                print("❌ Failed to read from camera")
                continue

            # Write the frame to the video file if recording
            if recording:
                out.write(img)

            hands, img = detector.findHands(img, draw=True)
            if hands:
                for hand in hands:
                    hand_type = "left" if hand["type"] == "Left" else "right"
                    fingers = detector.fingersUp(hand)
                    finger_names = list(instruments[current_instrument][hand_type].keys())

                    for i, finger in enumerate(finger_names):
                        if fingers[i] == 1 and prev_states[hand_type][finger] == 0:
                            play_chord(instruments[current_instrument][hand_type][finger])
                        elif fingers[i] == 0 and prev_states[hand_type][finger] == 1:
                            threading.Thread(target=stop_chord_after_delay, args=(instruments[current_instrument][hand_type][finger],), daemon=True).start()
                        prev_states[hand_type][finger] = fingers[i]
            else:
                for hand in instruments[current_instrument]:
                    for finger in instruments[current_instrument][hand]:
                        threading.Thread(target=stop_chord_after_delay, args=(instruments[current_instrument][hand][finger],), daemon=True).start()
                for hand in prev_states:
                    for finger in prev_states[hand]:
                        prev_states[hand][finger] = 0

            cv2.imshow("🎹 Air Piano Tracking", img)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("🛑 Quit signal received (Q pressed)")
                break
    except Exception as e:
        print(f"❌ Exception in hand tracking: {e}")
    finally:
        cap.release()
        out.release()  # Release the video writer
        cv2.destroyAllWindows()
        pygame.midi.quit()
        print("🛑 Hand tracking stopped and resources released.")

# 🌐 Frontend HTML
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Music Instrument Front Page</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" rel="stylesheet"/>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat&display=swap" rel="stylesheet"/>
  <style>
    body {
      font-family: "Montserrat", sans-serif;
    }
    .instrument-image {
      cursor: pointer;
      transition: transform 0.2s;
    }
    .instrument-image:hover {
      transform: scale(1.05);
    }
  </style>
</head>
<body class="bg-[#3a5365] relative min-h-screen overflow-hidden flex flex-col">

  <!-- Navigation -->
  <nav class="flex justify-center space-x-10 pt-8 text-white text-sm">
    <a class="font-light hover:underline" href="#">home</a>
    <a class="font-light hover:underline" href="#">about us</a>
    <a class="font-light hover:underline" href="#">payment</a>
    <a class="font-light hover:underline" href="#">options</a>
    <a class="font-light hover:underline" href="#">more</a>
  </nav>

  <!-- Main content container -->
  <main class="relative flex-grow flex flex-col items-center justify-center px-4">
    <div class="flex space-x-6 z-10">
      <img id="guitarImage" class="w-28 h-40 object-contain drop-shadow-lg instrument-image" src="https://storage.googleapis.com/a1aa/image/e1f0bd6a-9924-483a-5f8e-9637f728b9e3.jpg" alt="Electric guitar"/>
      <img id="sitarImage" class="w-24 h-40 object-contain drop-shadow-lg instrument-image" src="https://storage.googleapis.com/a1aa/image/d4be1bc0-f421-4012-592e-a830cea2eca8.jpg" alt="Sitar"/>
      <img id="drumImage" class="w-32 h-20 object-contain drop-shadow-lg instrument-image" src="https://storage.googleapis.com/a1aa/image/5ddeda2e-45c1-4f18-f782-9be8e13d151c.jpg" alt="Drum set"/>
      <img class="w-32 h-20 object-contain drop-shadow-lg instrument-image" src="https://storage.googleapis.com/a1aa/image/d2cfe984-705a-499e-84ae-e926a0c1b55a.jpg" alt="Keyboard piano"/>
    </div>
  </main>

  <!-- Bottom play/start buttons -->
  <div class="w-full max-w-[280px] mx-auto mb-10 flex flex-col items-center space-y-6 z-10">
    <h1 class="text-white text-6xl font-extrabold drop-shadow-[3px_3px_0_rgba(0,0,0,0.5)] leading-none text-center">PLAY</h1>
    <button id="startButton" class="bg-[#ef6f5f] text-white text-3xl font-semibold rounded-full px-14 py-3 shadow-lg hover:bg-[#e05a44] transition w-full">
      START
    </button>
    <button id="stopButton" class="bg-red-500 text-white text-3xl font-semibold rounded-full px-14 py-3 shadow-lg hover:bg-red-700 transition w-full">
      STOP
    </button>
    <button id="recordButton" class="bg-[#ef6f5f] text-white text-3xl font-semibold rounded-full px-14 py-3 shadow-lg hover:bg-[#e05a44] transition w-full">
      RECORD
    </button>
    <button id="viewVideoButton" class="bg-[#ef6f5f] text-white text-3xl font-semibold rounded-full px-14 py-3 shadow-lg hover:bg-[#e05a44] transition w-full">
      VIEW RECORDED VIDEO
    </button>
    <div class="w-48 h-6 bg-black bg-opacity-30 rounded-full shadow-lg"></div>
  </div>

  <!-- JavaScript to start, stop tracking, and change instruments -->
  <script>
    document.getElementById("startButton").addEventListener("click", () => {
      fetch("/start")
        .then(response => {
          if (response.ok) {
            console.log("✅ Hand tracking started.");
            alert("Hand tracking started! Switch to camera window.");
          } else {
            alert("⚠️ Failed to start tracking.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
          alert("Error starting hand tracking.");
        });
    });

    document.getElementById("stopButton").addEventListener("click", () => {
      fetch("/stop")
        .then(response => {
          if (response.ok) {
            console.log("🛑 Hand tracking stopped.");
            alert("Hand tracking stopped.");
          } else {
            alert("⚠️ Failed to stop tracking.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
          alert("Error stopping hand tracking.");
        });
    });

    document.getElementById("recordButton").addEventListener("click", () => {
      fetch("/start_recording")
        .then(response => {
          if (response.ok) {
            console.log("✅ Recording started.");
            alert("Recording started!");
          } else {
            alert("⚠️ Failed to start recording.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
          alert("Error starting recording.");
        });
    });

    document.getElementById("viewVideoButton").addEventListener("click", () => {
      window.open("/video", "_blank");
    });

    // Set instrument when image is clicked and play sound
    document.getElementById("guitarImage").addEventListener("click", () => {
      fetch("/set_instrument/guitar")
        .then(response => {
          if (response.ok) {
            console.log("✅ Instrument set to Guitar.");
            alert("Instrument set to Guitar.");
            playGuitarSound();
          } else {
            alert("⚠️ Failed to set instrument.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
          alert("Error setting instrument.");
        });
    });

    document.getElementById("sitarImage").addEventListener("click", () => {
      fetch("/set_instrument/sitar")
        .then(response => {
          if (response.ok) {
            console.log("✅ Instrument set to Sitar.");
            alert("Instrument set to Sitar.");
            playSitarSound();
          } else {
            alert("⚠️ Failed to set instrument.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
          alert("Error setting instrument.");
        });
    });

    document.getElementById("drumImage").addEventListener("click", () => {
      fetch("/set_instrument/drum")
        .then(response => {
          if (response.ok) {
            console.log("✅ Instrument set to Drum.");
            alert("Instrument set to Drum.");
            playDrumSound();
          } else {
            alert("⚠️ Failed to set instrument.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
          alert("Error setting instrument.");
        });
    });

    // Function to play sounds directly
    function playGuitarSound() {
      const notes = instruments["guitar"]["left"]["thumb"]; // Example: Play D Major
      playChord(notes);
    }

    function playSitarSound() {
      const notes = instruments["sitar"]["left"]["thumb"]; // Example: Play C Major
      playChord(notes);
    }

    function playDrumSound() {
      const notes = instruments["drum"]["left"]["thumb"]; // Example: Play Bass Drum
      playChord(notes);
    }

    function playChord(notes) {
      fetch(`/play_chord/${notes.join(',')}`)
        .then(response => {
          if (response.ok) {
            console.log("✅ Chord played.");
          } else {
            console.error("⚠️ Failed to play chord.");
          }
        })
        .catch(error => {
          console.error("❌ Error:", error);
        });
    }
  </script>
</body>
</html>
"""

# 🧠 Flask Routes
@app.route('/')
def home():
    return render_template_string(html_content)

@app.route('/start')
def start_tracking():
    global hand_tracking_running
    if not hand_tracking_running:
        print("🖱️ START button clicked from browser")
        threading.Thread(target=hand_tracking_loop, daemon=True).start()
    return "Hand Tracking Started"

@app.route('/stop')
def stop_tracking():
    global hand_tracking_running
    hand_tracking_running = False
    return "Hand Tracking Stopped"

@app.route('/start_recording')
def start_recording():
    global recording
    recording = True
    return "Recording started"

@app.route('/set_instrument/<instrument_name>')
def set_instrument(instrument_name):
    global current_instrument
    if instrument_name in instruments:
        current_instrument = instrument_name
        return f"Instrument set to {instrument_name}"
    return "Invalid instrument"

@app.route('/play_chord/<notes>')
def play_chord_route(notes):
    note_list = list(map(int, notes.split(',')))
    play_chord(note_list)
    return "Chord played"

@app.route('/video')
def serve_video():
    video_file = 'output.avi'
    if os.path.exists(video_file):
        return send_file(video_file, mimetype='video/x-msvideo')
    else:
        return "Video file not found. Please ensure recording was started and completed."

# 🚀 Run Flask
if __name__ == '__main__':
    app.run(debug=True)
