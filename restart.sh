killall luajit
cd /home/ubuntu/poemportraits/torch-rnn
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:`pwd`
/home/ubuntu/torch/install/bin/th sample_zoedtry.lua >>/home/ubuntu/poemportraits/torch-rnn.log.txt 2>&1 &
echo "TORCH SCRIPT RESTARTED"

sudo killall flask
cd /home/ubuntu/poemportraits
sudo FLASK_APP=poemportraits.py flask run --host=0.0.0.0 >>/home/ubuntu/poemportraits/poemportraits.log.txt 2>&1 &
echo "SERVER SCRIPT RESTARTED"
