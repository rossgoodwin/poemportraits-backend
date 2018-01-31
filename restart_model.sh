killall luajit
cd /home/ubuntu/poemportraits/torch-rnn
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:`pwd`
/home/ubuntu/torch/install/bin/th sample_zoedtry.lua >>/home/ubuntu/poemportraits/torch-rnn.log.txt 2>&1 &

