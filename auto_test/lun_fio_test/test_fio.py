#!/usr/bin/env python
import random
import paramiko
import time
import copy

gw_list = ['10.2.0.80', '10.2.0.81', '10.2.0.82']

def ssh2(ip,username,passwd,cmd):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip,22,username,passwd,timeout=5)
        stdin,stdout,stderr = ssh.exec_command(cmd)
        ssh.close()
    except :
        return 'error'

    return 'ok'

def sleep_10(ip, nic):
    print("test {} sleep 10".format(ip))
    ssh2(ip, "root", "r00tme", "ifconfig {} down; sleep 2; ifconfig {} up".format(nic, nic))

def sleep_16(ip,nic):
    print("test {} sleep 16".format(ip))
    ssh2(ip, "root", "r00tme", "ifconfig {} down; sleep 16; ifconfig {} up".format(nic, nic))

def get_rand(start, end):
    sleep_time = random.randint(start, end)
    print("sleep {}".format(sleep_time))
    return sleep_time

test_mod = {}

for gw in gw_list:
    test_mod[gw] = []
    test_mod[gw].append(sleep_10)
    test_mod[gw].append(sleep_16)

def test(glist):
    if len(glist) == 0:
        return
    ip_addr = glist.pop(0)
    for test_f in test_mod[ip_addr]:
        test_f(ip_addr, 'eth0')
        time.sleep(get_rand(0, 20))

        test(glist)

while True:
    gw_test = copy.copy(gw_list)
    test(gw_test)
    time.sleep(30)
