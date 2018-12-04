import os
import time
import io
import sys
import argparse
import subprocess
import time
import random
import paramiko
import atexit

from constants import PORT_START


def ssh_client_connect(ip, keyfile):
    ssh_client = paramiko.client.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.connect(ip,
        username="alexyu0",
        key_filename=keyfile)
    ch = ssh_client.get_transport().open_session()
    ch.get_pty()
    ch.set_combine_stderr(True)
    return (ssh_client, ch)

def server_iperf(ssh_ips, pmd_ips, test_dir, i, file_name, args):
    """
    starts iperf in server mode on each of the AWS instances defined by an
    entry in ips
    """
    ssh_info = []
    filenames = []
    for j in range(0, len(ssh_ips)):
        ssh_client, ch = ssh_client_connect(ssh_ips[j], args.keyfile)
        filename = "STDOUTDUMP_{}_server{}_{}".format(file_name, j+1, i)
        cmd = "iperf3 -s -B {} > {}_{}".format(
            pmd_ips[0], os.path.basename(test_dir), filename)
        print(cmd)
        ch.exec_command(cmd)
        print("server iperf for {} started".format(ssh_ips[j]))
        filenames.append(filename)
        ssh_info.append((ssh_client, ch))
    return (ssh_info, filenames)

def kill_server_iperf(ssh_info, filenames, test_dir):
    # wait to finish, then scp dumps
    for j in range(0, len(ssh_info)):
        (ssh_client, ch) = ssh_info[j]
        ch.close()
        ftp_client = ssh_client.open_sftp()
        ftp_client.get(
            "{}_{}".format(os.path.basename(test_dir), filenames[j]),
            "{}/{}".format(test_dir, filenames[j]))
        ssh_client.exec_command("rm {}_{}".format(os.path.basename(test_dir), filenames[j]))
        ssh_client.close()

def server_tcpdump(ips, test_dir, i, file_name, file_name_short, args):
    """
    starts tcpdump at the server endpoint
    """
    ssh_info = []
    filenames = []
    for j in range(0, len(ips)):
        time.sleep(1)
        ssh_client, ch = ssh_client_connect(ips[j], args.keyfile)
        fname = "{}_server{}_{}".format(file_name, j+1, i)
        cmd = "sudo tcpdump tcp -n -i enp6s0f0 -B 4096 port 5201 -w {}.pcap".format(
            fname)
        ch.exec_command(cmd)
        filenames.append(fname)
        ssh_info.append((ssh_client, ch))
    return (ssh_info, filenames)

def kill_server_tcpdump(ssh_info, filenames, test_dir):
    # wait to finish, then scp tcp dumps
    for j in range(0, len(ssh_info)):
        (ssh_client, ch) = ssh_info[j]
        ch.close()
        ssh_client.exec_command("pgrep tcpdump | xargs sudo kill -SIGINT")
        stdin, stdout, stderr = ssh_client.exec_command(
            "zstd --rm -19 -f {}.pcap -o {}.pcap.zst".format(
                filenames[j],
                filenames[j]))
        print("zstd --rm -19 -f {}.pcap -o {}.pcap.zst".format(
                filenames[j],
                filenames[j]))
        if stdout.channel.recv_exit_status() != 0:
            print(stderr)
            print("hi server")
            sys.exit(1)
        ftp_client = ssh_client.open_sftp()
        ftp_client.get(
            "{}.pcap.zst".format(filenames[j]),
            "{}/{}.pcap.zst".format(test_dir, filenames[j]))
        ssh_client.exec_command("rm {}_{}.pcap.zst".format(
            os.path.basename(test_dir), 
            filenames[j]))
        ssh_client.close()

def client_tcpdump(ips, test_dir, i, file_name, file_name_short, args):
    """
    starts tcpdump at the client endpoint
    """
    #client_tcpdump_procs = []
    filenames = []
    ssh_info = []
    for j in range(0, len(ips)):
        time.sleep(1)
        ssh_client, ch = ssh_client_connect(ips[j], args.keyfile)
        fname = "{}_client{}_{}".format(file_name, j+1, i)
        cmd = "sudo tcpdump tcp -n -i enp6s0f0 -B 4096 port {} -w {}.pcap".format(
            PORT_START + j,
            fname)
        ch.exec_command(cmd)
        #client_tcpdump_procs.append(subprocess.Popen([cmd],
        #    shell=True))
        filenames.append(fname)
        ssh_info.append((ssh_client, ch))
    return (ssh_info, filenames)

def kill_client_tcpdump(ssh_info, filenames, test_dir):
    for j in range(0, len(ssh_info)):
        (ssh_client, ch) = ssh_info[j]
        ch.close()
        ssh_client.exec_command("pgrep tcpdump | xargs sudo kill -SIGINT")
        stdin, stdout, stderr = ssh_client.exec_command(
            "zstd --rm -19 -f {}.pcap -o {}.pcap.zst".format(
                filenames[j],
                filenames[j]))
        print("zstd --rm -19 -f {}.pcap -o {}.pcap.zst".format(
                filenames[j],
                filenames[j]))
        if stdout.channel.recv_exit_status() != 0:
            print(stderr)
            print("hi client")
            sys.exit(1)
        ftp_client = ssh_client.open_sftp()
        ftp_client.get(
            "{}.pcap.zst".format(filenames[j]),
            "{}/{}.pcap.zst".format(test_dir, filenames[j]))
        ssh_client.exec_command("rm {}_{}.pcap.zst".format(
            os.path.basename(test_dir), 
            filenames[j]))
        ssh_client.close()

def cleanup(ssh_ips, keyfile):
    os.system("pgrep iperf3 | xargs sudo kill -9")
    os.system("pgrep tcpdump | xargs sudo kill -9")
    for ip in ssh_ips:
        ssh_client, ch = ssh_client_connect(ip, keyfile)
        ssh_client.exec_command("pgrep iperf3 | xargs sudo kill -9")
        ssh_client.exec_command("pgrep tcpdump | xargs sudo kill -9")
        ssh_client.close()

def test(args):
    """
    main testing function
    """
    # set up hosts
    # ips = []
    # with open(args.ips) as f:
    #     ips = f.read().strip().split("\n")
    #     ips = [ip for ip in ips if len(ip) > 0]
    # print("...hosts set up")
    ssh_ips = [
        "c220g2-011012.wisc.cloudlab.us", # server
        "c220g2-011011.wisc.cloudlab.us" # client
    ]
    pmd_ips = [
        "192.0.0.2", # server
        "192.0.0.4" # client
    ]

    # make file name
    duration = ""
    short_duration = ""
    if args.time is not None:
        duration = "-t {}".format(args.time)
        name_duration = "{}s".format(str(args.time))
        short_duration = "-t {}".format(int(int(args.time) * 0.01))
        name_short_duration = "{}s".format(str(int(int(args.time) * 0.01)))
    elif args.size is not None:
        duration = "--bytes {}".format(int(args.size) * 1000000)
        name_duration = "{}s".format(str(int(args.size) * 1000000))
        short_duration = "--bytes {}".format(int(int(args.size) * 10000))
        name_short_duration = "{}MB".format(str(int(int(args.size) * 10000)))
    file_name = "{}_{}".format(args.location, name_duration)
    file_name_short = ""
    if args.longshort:
        file_name_short = "{}_{}".format(args.location, name_short_duration)

    # set up test directory
    args.path = args.path.rstrip("/")
    root_test_dir = os.path.abspath(args.path)
    if args.concurrentlong:
        test_dir = "{}/{}/{}".format(root_test_dir, "concurrent_long", file_name)
        print("not supported right now")
        sys.exit(1)
    elif args.longshort:
        test_dir = "{}/{}/{}".format(root_test_dir, "long_and_short", file_name)
        print("not supported right now")
        sys.exit(1)
    elif args.normal:
        test_dir = "{}/{}/{}".format(root_test_dir, "normal", file_name)
    else:
        print("NO VALID TEST STYLE")
        sys.exit(1)
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    print("...test_dir {} set up".format(test_dir))
    atexit.register(cleanup, ssh_ips=ssh_ips, keyfile=args.keyfile)
    print("...cleanup registered")
    
    for i in range(1, int(args.numtests) + 1):
        print("\n\n STARTING TEST {}...".format(i))
        # local tcpdump 
        client_tcpdump_procs, c_t_filenames = client_tcpdump(
            [ssh_ips[1]], test_dir, i, file_name, file_name_short, args)
        print("...started local tcpdump {}".format(ssh_ips[1]))

        # remote ssh start iperf server
        iperf_ssh_info, s_i_filenames = server_iperf(
            [ssh_ips[0]], pmd_ips, test_dir, i, file_name, args)
        print("...started server iperf {}".format(ssh_ips[0]))

        # remote ssh tcpdump server side
        tcpdump_ssh_info, s_t_filenames = server_tcpdump(
            [ssh_ips[0]], test_dir, i, file_name, file_name_short, args)
        print("...started server tcpdump {}".format(ssh_ips[0]))

        # local iperf client start
        time.sleep(5) # let server get ready
        print("starting local iperf...")
        writers = []
        client_iperf_procs = []
        ssh_info = []
        ssh_client, ch = ssh_client_connect(ssh_ips[1], args.keyfile)
        #w = io.open("{}/STDOUTDUMP_{}_client{}_{}".format(test_dir, file_name, j+1, i), "wb")
        #writers.append(w)
        # if args.longshort and j == 1:
        #     cmd = "iperf3 --reverse --cport {} {} -c {}".format(
        #         PORT_START + j, 
        #         short_duration,
        #         ips[1])
        # else:
        cmd = "iperf3 -c {} -B {} --reverse --cport {} {} ".format(
            pmd_ips[0],
            pmd_ips[1],
            PORT_START, 
            duration)
        print(cmd)
        ssh_client.exec_command(cmd)

        #client_iperf_procs.append(subprocess.Popen(cmd,
        #    shell=True))#,
            #stdout=w))
        print("...started local iperfs")

        # wait to finish
        # if args.longshort:
        #     proc = client_iperf_procs[0]
        #     while proc.poll() is None:
        #         client_iperf_procs[1].wait()
        #         print("short client iperf done, going again")
        #         time.sleep(random.randint(10, 15))
        #         cmd = "iperf3 --reverse --cport {} {} -c {}".format(
        #             PORT_START + 1, 
        #             short_duration,
        #             ips[j])
        #         client_iperf_procs[1] = subprocess.Popen(cmd,
        #             shell=True,
        #             stdout=w)
        # else:
        if args.time is None:
            print("only use size")
            sys.exit(1)
        time.sleep((int(args.time) * 1.05))
            
        # kill all other stuff
        kill_client_tcpdump(client_tcpdump_procs, c_t_filenames, test_dir)
        kill_server_tcpdump(tcpdump_ssh_info, s_t_filenames, test_dir)
        kill_server_iperf(iperf_ssh_info, s_i_filenames, test_dir)
        print("...test {} done".format(i))
        time.sleep(1)
        ssh_client.close()

    return

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
parser = argparse.ArgumentParser(prog="PROG",
    description="829 Project Network Traces",
    usage="python run_test.py",
    formatter_class=formatter)

required_args = parser.add_argument_group("required")
required_args.add_argument("-l", "--location",
    help="location trace is taken in, used for file name\n")
# required_args.add_argument("-I", "--ips",
#     help="file containing list of server IPs, \n*** DON'T INCLUDE ENDPOINT OR TRIAL # ***\n")
required_args.add_argument("-P", "--path", 
    help="path to root directory of test results\n")
required_args.add_argument("-n", "--numtests", 
    help="number of times to run test\n")
required_args.add_argument("-i", "--keyfile",
    help="path to public key file\n")

test_args = parser.add_mutually_exclusive_group(required=True)
test_args.add_argument("-t", "--time",
    help="amount of time to run test for, in seconds\n")
test_args.add_argument("-s", "--size",
    help="size of data to be transmitted, in MB\n")

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
    random.seed()
    args = parser.parse_args()
    args.func(args)
