sudo killall flask
cd /home/ubuntu/poemportraits
sudo FLASK_APP=poemportraits.py flask run --host=0.0.0.0 >>/home/ubuntu/poemportraits/poemportraits.log.txt 2>&1 &
