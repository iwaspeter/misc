class HostgroupTest():
      def __init__(self, logger, group_list, iqn_list, disk_list):
          self.logger = logger
          self.group_list = group_list
          self.iqn_list = iqn_list
          self.disk_list = disk_list
          self.test_list = ['create', 'delete', 'add_host', 'remove_host', 'add_disk', 'remove_disk']

      def group_test(self, test_project):
