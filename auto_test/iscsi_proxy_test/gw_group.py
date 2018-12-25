class GWgroup():
      def __init__(self, logger, gw_list):
          self.logger = logger
          self.test_list = ['create', 'delete']
          self.gw_list = gw_list

      def group_test(self, test_value):

