#!/usr/bin/env python

class Table():
      def __init__(self, logger):
          self.table_info = {}
          self.logger = logger

      def table_create(self, table_name, table_attr, test_list):
          if table_name in self.table_info:
              return

          self.table_info[table_name] = {}
          self.table_info[table_name]['test_list'] = []
          self.table_info[table_name]['tuplist']  = []
          self.table_info[table_name]['table_attr'] = []

          self.table_info[table_name] = value

      def table_create(self):

      def get_table_fk(self, table_name):
