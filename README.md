# 829_project
15829 project

## Dump formats
### Naming
Dumps are named as (location)\_(test size)\_(endpoint)(client # for concurrent long tests)\_(run)

### CSV format
relative time, src port, dest port, seq, ack, len

## Dump collection
For each connection being simulated
1. on AWS instance server, run `iperf3 -s`
2. in separate window on AWS instance server, run 'sudo tcpdump port 5201 -w <file>`
2. in one window on laptop, run `sudo tcpdump port <port> -w <file>`
3. in one window on laptop, run `iperf3 --reverse --cport <port> --bytes <size> -c <AWS instance IP>
