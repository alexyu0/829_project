# 829_project
15829 project

## Go setup
Make sure this repo is under `src/github.com/alexyu0/` in a directory that
GOPATH points to
If `govendor` not installed, run `go get -u github.com/kardianos/govendor`
In root directory of repo, run `govendor sync` to install vendored dependencies
as listed in `vendor/vendor.json`

## Dump formats
### Naming
Dumps are named as `(location)\_(test size)\_(endpoint)(client # for concurrent long tests)\_(run)`

They are located in `test_dumps/(test_type)` and can be decompressed into .pcap
with `zstd <filename>.pcap.zstd -d -o <filename>.pcap`

### CSV format
relative time, src port, dest port, seq, ack, len

## Dump collection
1. Make sure you have `zstd` installed
    * `brew install zstd` for OSX
2. Run `sudo visudo`, then add a line with `Defaults:<your username> timestamp_timeout=60` to prevent sudo timing out during a test run
3. Use the script `scripts/run_test.py`
    * instructions can be seen with `pipenv run scripts/run_test.py -h`
    * e.g. `pipenv run python scripts/run_test.py -I aws_ips.txt -P . -n 2 -i ~/.ssh/829.pem -t 1 -N -l home`

## Running analysis
1. Run from the `829_project` directory.
2. The (time or size), type of test, and location need to match an existing test. In addition, specify the test directory and which analysis to run. 
	* e.g. `python3 scripts/run_analysis.py -P test_analysis -T test_dumps -G graphs -t 120 -L -l zhome -B`

## Other useful scripts
### Decompressing zstd to pcap
```
zstd <zstd file> -d -o <new file>
```

### pcap RTTs to csv
```
tshark -r <campus_100MB_1c_0l_client_1>.<1> -Y tcp.analysis.ack_rtt -e tcp.analysis.ack_rtt -T fields -E separator=, -E quote=d > rtt.csv
```

### pcap to csv
```
tshark -r ~/Documents/2018_Masters_Fall/15-829_Programmable_Networks/Project/829_project/tmp.pcap \
-Y "tcp" \
-e frame.time_relative \
-e ip.id \
-e tcp.srcport \
-e tcp.dstport \
-e tcp.seq \
-e tcp.ack \
-e tcp.len \
-T fields \
-E separator=, \
> ~/Documents/CMU/Masters/15829_15848_Project/829_project/new_csv/$1.csv
```
