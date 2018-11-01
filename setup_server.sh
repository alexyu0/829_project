sudo apt-get -y update
sudo apt-get -y upgrade
sudo apt-get -y install	build-essential

cd iperf
./configure
sudo make
sudo apt-get -y install lib32z1
sudo make install

