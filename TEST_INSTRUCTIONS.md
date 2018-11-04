1. ssh into AWS instance that will be server and run `iperf3 -s`
2. in one window on laptop, run `sudo tcpdump port <port> -w <file>`
3. in one window on laptop, run `iperf3 --reverse --cport <port> --bytes <size> -c <AWS instance IP>
