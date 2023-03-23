from flask import Flask, render_template, Response
import cv2
import zmq
import lz4.frame
import pickle
from time import time
import threading
import ssl


# camera = cv2.VideoCapture(0)



app = Flask(__name__)


# def gen_frames():  
#     while True:
#         success, frame = camera.read()  # read the camera frame
#         if not success:
#             break
#         else:
#             ret, buffer = cv2.imencode('.jpg', frame)
#             frame = buffer.tobytes()
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result
            

def gen_frames():
    context = zmq.Context()
    src = context.socket(zmq.SUB)
    src.connect("tcp://127.0.0.1:5557")
    src.setsockopt(zmq.SUBSCRIBE, b"")
    
    while True:
        # Receive frame and timestamp data from the ring buffer
        compressed_frame = src.recv()
        ts_frameno_data = src.recv_pyobj()
        ts = ts_frameno_data['ts']
        frameno = ts_frameno_data['frameno']
        
        # Decompress and deserialize the frame data
        frame_data = lz4.frame.decompress(compressed_frame)
        frame = pickle.loads(frame_data)
        
        # Encode the frame as JPEG and yield it
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        


# Start the ring buffer system in a separate thread
def run_ring_buffer():
    cap = cv2.VideoCapture('http://192.168.0.119:81/stream')

    context = zmq.Context()
    dst = context.socket(zmq.PUB)
    dst.bind("tcp://127.0.0.1:5557")
    frameno = 0
    COMPRESSED = True
    while True:
        ret, frame = cap.read()
        ts = time()
        frameno += 1
        if COMPRESSED:
            dst.send(lz4.frame.compress(pickle.dumps(frame)))
        else:
            dst.send_pyobj(frame)
        dst.send_pyobj(dict(ts=ts, frameno=frameno))
    
thread = threading.Thread(target=run_ring_buffer)
thread.start()

# # Start the Flask server
# if __name__ == "__main__":
#     app.run(debug=True)
       

@app.route("/")
def home():
    return render_template("home.html")
    
@app.route("/about")
def about():
    return render_template("about.html")

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
    # app.run(debug=True, host='192.168.0.174', port=5000)

    # app.run(debug=True, host='10.128.0.177')





