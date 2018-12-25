#!/usr/bin/env python
import random
import paramiko
import time
import copy
import sys
import json


def get_rand(start, end):
    sleep_time = random.randint(start, end)
    return sleep_time

def ssh2(ip,username,passwd,cmd, logger):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip,22,username,passwd,timeout=5)
        stdin,stdout,stderr = ssh.exec_command(cmd)
    except :
        logger.info("exec {} ssh error, the test will stop".format(ip))
        sys.exit(0)

    info = stdout.read().decode()
    ssh.close()
    return info

def get_hostgroup(logger, proxy_port, proxy_addr, user, password):
    hostgroup_info = ssh2(proxy_addr, user, password, "curl -X GET http://127.0.0.1:{}/api/hostgroups".format(proxy_port), logger)
    return json.loads(hostgroup_info)

def get_gwlist(logger, proxy_port, proxy_addr, user, password):
    gw_info = ssh2(proxy_addr, user, password, "curl -X GET http://127.0.0.1:{}/api/gateway_groups".format(proxy_port), logger)
    return json.loads(gw_info)

class TestCase():
    def __init__(self, logger, user, password, gateway_ip, nic):
        self.logger = logger
        self.user = user
        self.password = password
        self.ip = gateway_ip
        self.nic = nic

    def test_sleep_10(self):
        self.logger.info("test {} sleep 10".format(self.ip))
        ssh2(self.ip, self.user, self.password, "ifconfig {} down; sleep 2; ifconfig {} up".format(self.nic, self.nic), self.logger)

    def test_sleep_16(self, ip,nic):
        self.logger.info("test {} sleep 16".format(ip))
        ssh2(ip, self.user, self.password, "ifconfig {} down; sleep 16; ifconfig {} up".format(self.nic, self.nic), self.logger)

    def test_stop_tcmu(self):
        ssh2(ip, self.user, self.password, "systemctl stop tcmu-runner;sleep ; systemctl start tcmu-runner", self.logger)

    @classmethod
    def get_TestCase_methods(self):
        return filter(lambda x: x.startswith('test_') and callable(getattr(self,x)), dir(self))
