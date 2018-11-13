# 829_project
15829 project

## Dump formats
### Naming
Dumps are named as (location)\_(test size)\_(endpoint)(client # for concurrent long tests)\_(run)

### CSV format
relative time, src port, dest port, seq, ack, len

## Dump collection
Run `sudo visudo`, then add a line with `Defaults:<your username> timestamp_timeout=60` to prevent sudo timing out during a test run
Use the script `scripts/run_test.py`
 - instructions can be seen with `pipenv run scripts/run_test.py -h`
 - e.g. `pipenv run python scripts/run_test.py -f testtest -I aws_ips.txt -P . -n 2 -i ~/.ssh/829.pem -t 1 -N`
