from libtest import get_gwlist, TestCase, ssh2,get_hostgroup
import logging
import subprocess
import sys

logger = logging.getLogger('iscsi-test')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('/var/log/iscsi-test.log', mode='w')
file_handler.setLevel(logging.DEBUG)
file_format = logging.Formatter(
            "%(asctime)s %(levelname)8s [%(filename)s:%(lineno)s:%(funcName)s()] "
            "- %(message)s")
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

PROXY_PORT = 5002
PROXY_ADDR = '192.168.2.85'
PROXY_USR = 'root'
PROXY_PASSWD = 'r00tme'
GATEWAY_USER = 'root'
GATEWAY_PASSWD = 'r00tme'
LOG_LEVEL = 0

def log_output(info, logger):
    if LOG_LEVEL == 0:
        print(info)
    else:
        logger.info(info)


def init_iscsi_initiator(initiator_name, user, passwd, logger):
    try:
       subprocess.check_output('sed -i \'s/InitiatorName=.*$/InitiatorName={}/\' /etc/iscsi/initiatorname.iscsi'.format(initiator_name), shell=True)
    except:
       log_output("init iscsi initiatorname.iscsi file failed", logger)
       sys.exit(0)

    try:
       subprocess.check_output('sed -i \'s/node.session.timeo.replacement_timeout = .*$/node.session.timeo.replacement_timeout = 10/\' /etc/iscsi/iscsid.conf'.format(initiator_name), shell=True)
    except:
       log_output("init iscsi initiatorname.iscsi file failed", logger)
       sys.exit(0)
    try:
       subprocess.check_output('sed -i \'s/node.session.err_timeo.abort_timeout = .*$/node.session.err_timeo.abort_timeout = 10/\' /etc/iscsi/iscsid.conf'.format(initiator_name), shell=True)
    except:
       log_output("init iscsi initiatorname.iscsi file failed", logger)
       sys.exit(0)

    if user == '' or passwd == '':
        try:
           subprocess.check_output('systemctl restart iscsid'.format(initiator_name), shell=True)
        except:
           log_output("restart iscsid failed", logger)
           sys.exit(0)
        return

    try:
       subprocess.check_output("sed -i 's/\^\#\(node.*CHAP\)$/\\1/' /etc/iscsi/iscsid.conf", shell=True)
    except:
       log_output("init iscsi.conf file failed",logger)
       sys.exit(0)
    try:
       subprocess.check_output("sed -i 's/^#\(node.*CHAP\)$/\\1/' /etc/iscsi/iscsid.conf", shell=True)
    except:
       log_output("init iscsi.conf file failed", logger)
       sys.exit(0)
#set initiator user
    try:
       subprocess.check_output("sed -i 's/^#\(node.session.auth.username_in = \).*$/\\1{}/' /etc/iscsi/iscsid.conf".format(user), shell=True)
    except:
       log_output("init iscsi.conf file failed", logger)
       sys.exit(0)

    print("user {} password {}".format(user, passwd))
    try:
       subprocess.check_output("sed -i \'s/^#\(node.session.auth.password_in = \).*$/\\1{}/\' /etc/iscsi/iscsid.conf".format(passwd), shell=True)
    except:
       log_output("init iscsi.conf file failed", logger)
       sys.exit(0)

    try:
       subprocess.check_output('systemctl restart iscsid'.format(initiator_name), shell=True)
    except:
       log_output("restart iscsid failed", logger)
       sys.exit(0)

def login_iscsi_target(ip_list ,logger):
    try:
        subprocess.check_output('iscsiadm -m node -u', shell=True).split('\n')
    except:
        print('ok')

    print("ok {}".format(ip_list[0]))
    try:
       gw_list = subprocess.check_output('iscsiadm -m discovery -t st -p {}'.format(ip_list[0]), shell=True).strip('\n').split('\n')
    except:
       log_output("discovery  failed", logger)
       sys.exit(0)

    if len(gw_list) != len(ip_list):
        print(gw_list, ip_list)
        log_output("discovery error ", logger)
        sys.exit(0)

    target_iqn = gw_list[0].split(' ')[1]

    try:
       subprocess.check_output('iscsiadm -m node -T {} -l'.format(target_iqn), shell=True)
    except:
       log_output("discovery  failed", logger)
       sys.exit(0)


def get_test_nic(ip_list):
    for ip in ip_list:
        nic,other_ip = ssh2(ip, GATEWAY_USER, GATEWAY_PASSWD)

def init_env():
    info = get_gwlist(logger, PROXY_PORT, PROXY_ADDR, PROXY_USR, PROXY_PASSWD)['message']
    ip_list = []
    gwg_name = ''
    print info
    for gwg in info:
        if len(gwg['gw_list']) < 1:
            continue
        if len(gwg['clients']) > 0:
            continue

        for gw in gwg['gw_list']:
            if gw['status'] != 'ok':
                ip_list = []
                break

            ip_list.append(gw['ipaddr'])

        if len(ip_list) > 1:
            gwg_name = gwg['name']
            break

    if len(ip_list) == 0:
        log_output("not found gateway", logger)
        sys.exit(0)

    info = get_hostgroup(logger, PROXY_PORT, PROXY_ADDR, PROXY_USR, PROXY_PASSWD)['message']
    initiator_name = ''
    group_chap_user = ''
    group_chap_passwd = ''
    for group_name in info:
        gw_groups = info[group_name]['gw_groups']
        if len(gw_groups) > 1:
            log_output("only support 1 gateway group")
            sys.exit(0)

        gw_group = gw_groups[0]
        if gw_group != gwg_name:
            continue

        hosts = info[group_name]['hosts']
        disks = info[group_name]['disks']
        if len(hosts) == 0 or len(disks) == 0:
            continue


        initiator_name = hosts[0]
        if 'chap' in info[group_name]:
            group_chap_user = info[group_name]['chap']['user']
            group_chap_passwd = info[group_name]['chap']['password']

        break

    if initiator_name == '':
        log_output("not found hostgroup info", logger)
        sys.exit(0)
    log_output("begin init iscsi config", logger)
    init_iscsi_initiator(initiator_name, group_chap_user, group_chap_passwd, logger)
    log_output("begin login iscsi", logger)
    login_iscsi_target(ip_list, logger)

if __name__ == '__main__':
    init_env()
#test_case = TestCase.get_TestCase_methods()
