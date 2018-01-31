from flask import Flask, request, redirect, flash, url_for, send_from_directory
# from twilio.twiml.messaging_response import MessagingResponse
from socket_sender import WordCamera
from flask_cors import CORS
# from flask_mail import Mail, Message
from flask_socketio import SocketIO, send, emit
import time
import urllib.request
import os
import subprocess
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])
UPLOAD_FOLDER = '/home/ubuntu/poemportraits/img'

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'rocketbananafuelcycleorangetips'

server_ip = '54.191.216.93'

# mail = Mail(app)

CORS(app)
# app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

wc = WordCamera(sentence_count=2, seed_ix=0, manual=False, looper=False)

narration_stack = list()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def hello():
    return "<h1 style='color:blue'>Hello There!</h1>"

@app.route("/restart")
def restart():
    proc = subprocess.Popen(['bash', '/home/ubuntu/poemportraits/restart.sh'])
    return "<h1>restarting server scripts...</h1>"

@app.route("/word/<input_word>")
def word(input_word):
    send({'word': input_word}, namespace='/narration', broadcast=True, json=True)
    return input_word

@app.route("/sms", methods=['GET', 'POST'])
def sms_word():
    """Respond to incoming calls with a simple text message."""
    # sms_from_number = request.values.get('From', None)
    sms_body = request.values.get('word', None)

    if sms_body:
        hid = wc.capture(sms_body)

        time.sleep(4)

        with open('/home/ubuntu/poemportraits/pages/%s.txt' % hid) as infile:
            narration = infile.read().strip().replace('\n', ' ')

        send({'narration': narration, 'word': sms_body.strip()}, namespace='/narration', broadcast=True, json=True)

        # resp = MessagingResponse().message(narration)

        narration_stack.append(narration)

        return str(narration)

@app.route("/img", methods=['GET', 'POST'])
def img_url():
    # img_url = request.values.get('url', None)
    # print(img_url)

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):

            filename = secure_filename(file.filename)

            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            img_url = url_for('uploaded_file', filename=filename)

            emit('img_url', {'url': 'http://'+server_ip+':5000'+img_url}, broadcast=True, namespace='/img_url')

            return redirect(img_url)

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/confirm", methods=['GET', 'POST'])
def confirm_img():
    img_url = request.values.get('url', None)
    confirmed = bool(int(request.values.get('confirmed', None)))

    send({'confirmed': confirmed, 'url': img_url}, namespace='/narration', broadcast=True, json=True)

    return str(confirmed)

@app.route("/email", methods=['GET', 'POST'])
def send_email():
    img_url = request.values.get('url', None)
    email = request.values.get('email', None)

    fn = '/home/ubuntu/poemportraits/img/%s' % img_url.rsplit('/', 1).pop()
    # urllib.request.urlretrieve(img_url, fn)

    if narration_stack:
        last_narration = narration_stack.pop().replace(', ', '\n').replace(',', '')
    else:
        last_narration = ""

    with open('/home/ubuntu/poemportraits/email.log.txt', 'a') as outfile:
        outfile.write(email+'\n')

    proc = subprocess.Popen(['mail', '-a', 'From: Poem Portraits <no-reply@poemportraits.com>', '-s', 'Your POEMPORTRAIT by Es Devlin', '-A', fn, email], stdin=subprocess.PIPE)
    proc.communicate(b"Your POEMPORTRAIT is attached. Thanks for taking part.\n\n__________________\n\n%s\n\n#esdevlin #madebygoogle\n\n__________________\n\nThis is a collaboration with Es Devlin and Google Arts and Culture working with creative technologist Ross Goodwin\n\ng.co/artsandculture   @googlearts\n\nPowered by Pixel" % last_narration.encode('utf8'))

    # msg = Message("Hello",
    #        sender="donotreply@poemportraits.com",
    #        recipients=[email])

    # msg.body = "Attached is your POEMPORTRAIT."

    # mail.send(msg)

    return str(img_url)



if __name__ == "__main__":
    socketio.run(app)

