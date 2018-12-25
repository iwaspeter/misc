#!/usr/bin/env python

class TestRes():
      def __init__(self, logger):
          self.logger = logger

      def get_gateway_status(self, gwg_mesg):
          gwg_info = gwg_mesg['message']
          ret_info = {}
          for gwg in gwg_info:
               gwg_name = gwg['name']
               ret_info[gwg_name] = {}
               for gw in gwg['gw_list']:
                   if gw['status'] != 'ok':
                       ret_info[gwg_name][gw['ipaddr']] = gw_status

          return ret_info

      def check_gwgroup_info(self, gwgroups_mesg, current_info):
           gwgroup_info = hostgroup_mesg['message']
           res_gwg_info = {}
           res_gwg_info['gwg_name'] = []
           for gwgroup in hostgroup_info:
               gwg_name = gwgroup['name']
               res_gwg_info['gwg_name'].append(gwg_name)
               res_gwg_info[gwg_name] = []
               for gw in gwg['gw_list']:
                   res_gwg_info[gwg_name].append(gw['ipaddr'])

           cur_gwgroup_set = set(current_info['gwg_name'])
           res_gwgroup_set = set(res_gwg_info['gwg_name'])
           if cur_gwgroup_set.sort() != res_gwgroup_set.sort():
               print("gwgroup set error".format(cur_gwgroup_set, res_gwgroup_set))
               sys.exit(0)

      def check_hostgroup_info(self, hostgroup_mesg, current_info):
          hostgroup_info = hostgroup_msg['message']

          for group_name in hostgroup_info:
              cur_disk_set = set(current_info[group_name]['disks'])
              res_disk_set = set(hostgroup_info[group_name]['disks'])
              if cur_disk_set.sort() != res_disk_set.sort():
                  print("disk set error".format(cur_disk_set, res_disk_set))
                  sys.exit(0)

              cur_host_set = set(current_info[group_name]['hosts'])
              res_host_set = set(hostgroup_info[group_name]['hosts'])
              if cur_host_set.sort() != res_host_set.sort():
                  print("host set error {} {}".format(cur_host_set, res_host_set))
                  sys.exit(0)


              gw_group_set = set([])
              for disk in list(cur_disk_set):
                  gw_group = self.get_disk_gwgroup_info(disk)
                  gw_group_set.add(gw_group)

              cur_group_set = set(current_info[group_name]['gw_groups'])
              if cur_group_set.sort() != gw_group_set.sort():
                  print("gw group set error".format(cur_group_set, gw_group_set))
                  sys.ext(0)

      def check_disk_info(self, disk_mesg, current_info):
          res_disk_info = disk_mesg['mesg']
          res_disk_set = set(res_disk_info.keys())
          cur_disk_set = set(current_info)
          if res_disk_set.sort() != cur_disk_set.sort():
              print("disk set error".format(res_disk_set, cur_disk_set))
              sys.exit(0)

