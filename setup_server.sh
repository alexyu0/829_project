sudo apt-get update
sudo apt-get upgrade
sudo apt-get install build-essential \
	lib32z1

cd iperf
./configure
sudo make
sudo make install

