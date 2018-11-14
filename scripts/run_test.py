import os
import time
import io
import sys
import argparse
import threading
import subprocess
import time
import paramiko

from constants import PORT_START

class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, group=None, target=None, name=None, verbose=None, args=(), kwargs=None):
        super().__init__()
        self._stop_event = threading.Event()
        self._target = target
        self._args = args

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

def server_iperf_worker(ips, test_dir, i, args):
    """
    starts iperf in server mode on each of the AWS instances defined by an
    entry in ips
    """
    ssh_info = []
    filenames = []
    for j in range(0, len(ips)):
        ssh_client = paramiko.client.SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(ips[j], 
            username="ubuntu",
            key_filename=args.keyfile)
        ch = ssh_client.get_transport().open_session()
        ch.get_pty()
        ch.set_combine_stderr(True)
        filename = "IPERFDUMP_{}_server{}_{}".format(args.fname, j+1, i)
        cmd = "iperf3 -s > {}_{}".format(
            os.path.basename(test_dir), filename)
        ch.exec_command(cmd)
        print("server iperf for {} started".format(ips[j]))
        filenames.append(filename)
        ssh_info.append((ssh_client, ch))

    # wait to finish, then scp dumps
    while not threading.current_thread().stopped():
        time.sleep(0.5)
    for j in range(0, len(ssh_info)):
        (ssh_client, ch) = ssh_info[j]
        ch.close()
        ftp_client = ssh_client.open_sftp()
        ftp_client.get(
            "{}_{}".format(os.path.basename(test_dir), filenames[j]),
            "{}/{}".format(test_dir, filenames[j]))
        ssh_client.exec_command("rm {}_{}".format(os.path.basename(test_dir), filenames[j]))
        ssh_client.close()

def tcpdump_worker(ips, is_client, test_dir, i, args):
    """
    starts tcpdump at the endpoint specified by is_client
    """
    if is_client:
        # client
        client_tcpdump_procs = []
        filenames = []
        for j in range(0, len(ips)):
            fname = "{}/{}_client{}_{}.pcap".format(test_dir, args.fname, j+1, i)
            cmd = "sudo tcpdump -i any port {} -w {}".format(
                PORT_START + j,
                fname)
            client_tcpdump_procs.append(subprocess.Popen([cmd],
                shell=True))
            filenames.append(fname)

        # wait to finish, then kill tcpdump
        while not threading.current_thread().stopped():
            time.sleep(0.5)
        for j in range(0, len(client_tcpdump_procs)):
            os.system("pgrep tcpdump | xargs sudo kill -SIGTERM")
            os.system("zstd --rm -f {} -o {}.zst".format(filenames[j], filenames[j]))
    else:
        # server
        ssh_info = []
        filenames = []
        for j in range(0, len(ips)):
            ssh_client = paramiko.client.SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(ips[j], 
                username="ubuntu",
                key_filename=args.keyfile)
            ch = ssh_client.get_transport().open_session()
            ch.get_pty()
            ch.set_combine_stderr(True)
            fname = "{}_server{}_{}".format(args.fname, j+1, i)
            cmd = "sudo tcpdump port 5201 -w {}_{}.pcap".format(
                os.path.basename(test_dir), 
                fname)
            ch.exec_command(cmd)
            filenames.append(fname)
            ssh_info.append((ssh_client, ch))

        # wait to finish, then scp tcp dumps
        while not threading.current_thread().stopped():
            time.sleep(0.5)
        for j in range(0, len(ssh_info)):
            (ssh_client, ch) = ssh_info[j]
            ch.close()
            ssh_client.exec_command("pgrep tcpdump | xargs sudo kill -SIGTERM")
            ssh_client.exec_command("zstd --rm -f {}_{}.pcap -o {}_{}.pcap.zst".format(
                os.path.basename(test_dir), 
                filenames[j],
                os.path.basename(test_dir), 
                filenames[j]))
            ftp_client = ssh_client.open_sftp()
            ftp_client.get(
                "{}_{}.pcap.zst".format(os.path.basename(test_dir), filenames[j]),
                "{}/{}.pcap.zst".format(test_dir, filenames[j]))
            ssh_client.exec_command("rm {}_{}.pcap.zst".format(
                os.path.basename(test_dir), 
                filenames[j]))
            ssh_client.close()

def test(args):
    """
    main testing function
    """
    # set up hosts
    ips = []
    with open(args.ips) as f:
        ips = f.read().split("\n")
    print("...hosts set up")

    # set up test directory
    root_test_dir = os.path.abspath(args.path)
    if args.concurrentlong:
        test_dir = "{}/{}".format(root_test_dir, "concurrent_long")
    elif args.longshort:
        test_dir = "{}/{}".format(root_test_dir, "long_and_short")
    elif args.normal:
        test_dir = "{}/{}".format(root_test_dir, "normal")
        ips = [ips[0]] # only 1 server
    else:
        print("NO VALID TEST STYLE")
        sys.exit(1)
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    print("...test_dir {} set up".format(test_dir))
    
    for i in range(1, int(args.numtests) + 1):
        print("\n\n STARTING TEST {}...".format(i))
        # local tcpdump 
        client_tcpdump_thread = StoppableThread(target=tcpdump_worker, 
            args=(ips, True, test_dir, i, args))
        client_tcpdump_thread.start()
        print("...started local tcpdump thread")
        if (i == 1):
            time.sleep(10) # give you time to enter password

        # remote ssh start iperf server
        server_iperf_thread = StoppableThread(target=server_iperf_worker, 
            args=(ips, test_dir, i, args))
        server_iperf_thread.start()
        print("...started server iperf thread")

        # remote ssh tcpdump server side
        server_tcpdump_thread = StoppableThread(target=tcpdump_worker, 
            args=(ips, False, test_dir, i, args))
        server_tcpdump_thread.start()
        print("...started server tcpdump thread")

        # local iperf client start
        time.sleep(5) # let server get ready
        print("starting local iperf...")
        duration = ""
        if args.time is not None:
            duration = "-t {}".format(args.time)
        elif args.size is not None:
            duration = "--bytes {}".format(args.size)

        writers = []
        client_iperf_procs = []
        for j in range(0, len(ips)):
            w = io.open("{}/IPERFDUMP_{}_client{}_{}".format(test_dir, args.fname, j+1, i), "wb")
            writers.append(w)
            cmd = "iperf3 --reverse --cport {} {} -c {}".format(
                PORT_START + j, 
                duration,
                ips[j])
            client_iperf_procs.append(subprocess.Popen(cmd,
                shell=True,
                stdout=w))

        # wait to finish
        for j in range(0, len(client_iperf_procs)):
            proc = client_iperf_procs[j]
            while proc.poll() is None:
                time.sleep(0.5)
            writers[j].close()
            
        # kill all threads
        client_tcpdump_thread.stop()
        server_tcpdump_thread.stop()
        server_iperf_thread.stop()
        client_tcpdump_thread.join()
        server_tcpdump_thread.join()
        server_iperf_thread.join()
        print("...test {} done".format(i))

    return

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
parser = argparse.ArgumentParser(prog="PROG",
    description="829 Project Network Traces",
    usage="python run_test.py",
    formatter_class=formatter)

required_args = parser.add_argument_group("required")
required_args.add_argument("-f", "--fname",
    help="file name for trace dump, format <location>_<duration or size of test>\n")
required_args.add_argument("-I", "--ips",
    help="file containing list of server IPs, \n*** DON'T INCLUDE ENDPOINT OR TRIAL # ***\n")
required_args.add_argument("-P", "--path", 
    help="path to root directory of test results\n")
required_args.add_argument("-n", "--numtests", 
    help="number of times to run test\n")
required_args.add_argument("-i", "--keyfile",
    help="path to public key file\n")

test_args = parser.add_mutually_exclusive_group(required=True)
test_args.add_argument("-t", "--time",
    help="amount of time to run test for\n")
test_args.add_argument("-s", "--size",
    help="size of data to be transmitted\n")

test_style_args = parser.add_mutually_exclusive_group(required=True)
test_style_args.add_argument("-C", "--concurrentlong",
    action="store_true",
    help="true if running concurrent long downloads test, false otherwise")
test_style_args.add_argument("-L", "--longshort",
    action="store_true",
    help="true if running long download with short downloads throughout test, false otherwise")
test_style_args.add_argument("-N", "--normal",
    action="store_true",
    help="true if running normal download test, false otherwise")

parser.set_defaults(func=test)

if __name__ == '__main__':
    args = parser.parse_args()
    args.func(args)
