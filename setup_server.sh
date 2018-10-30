sudo apt-get -y update
sudo apt-get -y upgrade
sudo apt-get -y install \
	build-essential \
	lib32z1

cd iperf
./configure
sudo make
sudo make install

