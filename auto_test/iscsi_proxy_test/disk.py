import random

class DiskTest():
      def __init__(self, logger, disk_list, table):
          self.logger = logger
          self.disk_list = disk_list
          self.max_size = 128 * 1024 * 1024 * 1024 * 1024
          self.min_size = 1024 * 1024
          self.pool = 'rbd'
          self.table = table
          test_list = DiskTest.get_TestCase()
          self.table.create('disk', ['disk', 'size', 'pool', 'gwgroup', 'hostgroup'], test_list)

      def check_size(size):
          if size > self.max_size or size < self.min_size:
              return False

      def get_size(self, is_true):
          while True:
             size = random.randint(0,  1024 * 1024 * 1024 * 1024 * 1024)
             if is_true == True:
                 size = (size / 1024 / 1024) * 1024 * 1024

             if check_size(size) is is_true:
                 return size

      def check_pool(self, is_true):

      def get_pool(self, is_true):
          pool_name = get_pool_name()
          if check_pool(pool_name) is is_true:
              return pool_name

      def test_resize(self, disk_name, is_true):
      def test_create(self, is_true):
      def test_remove(self, is_true):
      def test_convert(self, is_true):
      def test_update_gwgroup(self, disk_name, gwgroup, is_true):
      def test_update_hostgroup(self, disk_name, hostgroup, is_true):
      @classmethod
      def get_TestCase_methods(self):
          return filter(lambda x: x.startswith('test_') and callable(getattr(self,x)), dir(self))

