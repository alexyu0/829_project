sudo apt-get update
sudo apt-get upgrade
sudo apt-get install build-essential
git clone https://github.com/esnet/iperf.git   
cd iperf
./configure
sudo make
sudo make install

