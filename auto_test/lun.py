#!/usr/bin/env python

import os
import rados
import rbd

from time import sleep
from socket import gethostname
import requests
from requests import Response

from rtslib_fb import UserBackedStorageObject, root
from rtslib_fb.utils import RTSLibError, RTSLibNotInCFS
from rtslib_fb.alua import ALUATargetPortGroup

import ceph_iscsi_config.settings as settings

from ceph_iscsi_config.common import Config
# from ceph_iscsi_config.alua import ALUATargetPortGroup
from ceph_iscsi_config.utils import (convert_2_bytes, gen_control_string,
                                     get_pool_id, valid_size)

from ceph_iscsi_config.utils import WWN

__author__ = 'pcuzner@redhat.com'


class RBDDev(object):

    rbd_feature_list = ['RBD_FEATURE_LAYERING', 'RBD_FEATURE_EXCLUSIVE_LOCK',
                        'RBD_FEATURE_OBJECT_MAP', 'RBD_FEATURE_FAST_DIFF',
                        'RBD_FEATURE_DEEP_FLATTEN']

    def __init__(self, image, size, pool='rbd'):
        self.image = image
        self.size = size
        self.size_bytes = convert_2_bytes(size)
        self.pool = pool
        self.pool_id = get_pool_id(pool_name=self.pool)
        self.error = False
        self.error_msg = ''
        self.changed = False

    def create(self):
        """
        Create an rbd image compatible with exporting through LIO to multiple
        clients
        :return: status code and msg
        """

        with rados.Rados(conffile=settings.config.cephconf) as cluster:
            with cluster.open_ioctx(self.pool) as ioctx:
                rbd_inst = rbd.RBD()
                try:
                    rbd_inst.create(ioctx,
                                    self.image,
                                    self.size_bytes,
                                    features=RBDDev.supported_features(),
                                    old_format=False)

                except (rbd.ImageExists, rbd.InvalidArgument) as err:
                    self.error = True
                    self.error_msg = ("Failed to create rbd image {} in "
                                     "pool {} : {}".format(self.image,
                                                           self.pool,
                                                           err))

    def delete(self):
        """
        Delete the current rbd image
        :return: nothing, but the objects error attribute is set if there
        are problems
        """

        rbd_deleted = False
        with rados.Rados(conffile=settings.config.cephconf) as cluster:
            with cluster.open_ioctx(self.pool) as ioctx:
                rbd_inst = rbd.RBD()

                ctr = 0
                while ctr < settings.config.time_out:

                    try:
                        rbd_inst.remove(ioctx, self.image)
                    except rbd.ImageBusy:
                        # catch and ignore the busy state - rbd probably still mapped on
                        # another gateway, so we keep trying
                        pass
                    else:
                        rbd_deleted = True
                        break

                    sleep(settings.config.loop_delay)
                    ctr += settings.config.loop_delay

                if rbd_deleted:
                    return
                else:
                    self.error = True


    def rbd_size(self, native=0):
        """
        Confirm that the existing rbd image size, matches the requirement
        passed in the request - if the required size is > than
        current, resize the rbd image to match
        :return: boolean value reflecting whether the rbd image was resized
        """

        with rados.Rados(conffile=settings.config.cephconf) as cluster:
            with cluster.open_ioctx(self.pool) as ioctx:
                with rbd.Image(ioctx, self.image) as rbd_image:

                    # get the current size in bytes
                    current_bytes = rbd_image.size()

                    if self.size_bytes > current_bytes or native:

                        # resize method, doesn't document potential exceptions
                        # so using a generic catch all (Yuk!)
                        try:
                            rbd_image.resize(self.size_bytes)
                        except:
                            self.error = True
                            self.error_msg = ("rbd image resize failed for "
                                              "{}".format(self.image))
                        else:
                            self.changed = True

    def _get_size_bytes(self):
        """
        Return the current size of the rbd image
        :return: (int) rbd image size in bytes
        """

        with rados.Rados(conffile=settings.config.cephconf) as cluster:
            with cluster.open_ioctx(self.pool) as ioctx:
                with rbd.Image(ioctx, self.image) as rbd_image:
                    image_size = rbd_image.size()

        return image_size

    @staticmethod
    def rbd_list(conf=None, pool='rbd'):
        """
        return a list of rbd images in a given pool
        :param pool: pool name (str) to return a list of rbd image names for
        :return: list of rbd image names (list)
        """

        if conf is None:
            conf = settings.config.cephconf

        with rados.Rados(conffile=conf) as cluster:
            with cluster.open_ioctx(pool) as ioctx:
                rbd_inst = rbd.RBD()
                rbd_names = rbd_inst.list(ioctx)
        return rbd_names

    def _valid_rbd(self):

        valid_state = True
        with rados.Rados(conffile=settings.config.cephconf) as cluster:
            ioctx = cluster.open_ioctx(self.pool)
            with rbd.Image(ioctx, self.image) as rbd_image:

                if rbd_image.features() & RBDDev.required_features() != \
                    RBDDev.required_features():
                    valid_state = False

        return valid_state

    @classmethod
    def supported_features(cls):
        """
        Return an int representing the supported features for LIO export
        :return: int
        """
        # build the required feature settings into an int
        feature_int = 0
        for feature in RBDDev.rbd_feature_list:
            feature_int += getattr(rbd, feature)

        return feature_int

    @classmethod
    def required_features(cls):
        """
        Return an int representing the required features for LIO export
        :return: int
        """
        return rbd.RBD_FEATURE_EXCLUSIVE_LOCK

    current_size = property(_get_size_bytes,
                            doc="return the current size of the rbd(bytes)")

    valid = property(_valid_rbd,
                     doc="check the rbd is valid for export through LIO"
                         " (boolean)")


class LUN(object):

    def __init__(self, logger, pool, image, size, config):
        self.logger = logger
        self.image = image
        self.pool = pool
        self.pool_id = 0
        self.size = size
        self.size_bytes = convert_2_bytes(size)
        self.config_key = '{}.{}'.format(self.pool, self.image)
        self.controls = {}

        self.owner = ''     # gateway that owns the preferred path for this LUN
        self.error = False
        self.error_msg = ''
        self.num_changes = 0

        self.config = config

        self._validate_request()
        if self.config_key in self.config.config['disks']:
            self.controls = self.config.config['disks'][self.config_key].get('controls', {})

    def _get_max_data_area_mb(self):
        max_data_area_mb = self.controls.get('max_data_area_mb', None)
        if max_data_area_mb is None:
            return settings.config.max_data_area_mb
        return max_data_area_mb

    def _set_max_data_area_mb(self, value):
        if value is None or str(value) == str(settings.config.max_data_area_mb):
            self.controls.pop('max_data_area_mb', None)
        else:
            self.controls['max_data_area_mb'] = value

    max_data_area_mb = property(_get_max_data_area_mb, _set_max_data_area_mb,
                                doc="get/set kernel data area (MiB)")

    def _validate_request(self):
        if not rados_pool(pool=self.pool):
            # Could create the pool, but a fat finger moment in the config
            # file would mean rbd images get created and mapped, and then need
            # correcting. Better to exit if the pool doesn't exist
            self.error = True
            self.error_msg = ("Pool '{}' does not exist. Unable to "
                              "continue".format(self.pool))

    def remove_lun_lio(self):
        lun = self.lio_stg_object()
        if not lun:
            return

        self.remove_dev_from_lio()
        if self.error:
            return

	return
    def remove_lun(self):
        #self.remove_lun_lio()
        rbd_image = RBDDev(self.image, '0G', self.pool)
        rbd_image.delete()
        if rbd_image.error:
            self.error = True
            self.error_msg = ("Unable to delete the underlying rbd "
                              "image {}".format(self.config_key))
        return


    def remove_lun_config(self):
        if self.error == 'True':
            return self.error_msg
        # determine which host was the path owner
        disk_owner = self.config.config['disks'][self.config_key]['owner']
        # remove the definition from the config object
        self.config.del_item('disks', self.config_key)
        gw_metadata = self.config.config['gateways'][disk_owner]
        if gw_metadata['active_luns'] > 0:
            gw_metadata['active_luns'] -= 1
            self.config.update_item('gateways',
                                    disk_owner,
                                    gw_metadata)
    	return 'ok'

    def convert_lun_config(self):
        disk_owner = self.config.config['disks'][self.config_key]['owner']
        # remove the definition from the config object
        self.config.del_item('disks', self.config_key)
        gw_metadata = self.config.config['gateways'][disk_owner]
        if gw_metadata['active_luns'] > 0:
            gw_metadata['active_luns'] -= 1
            self.config.update_item('gateways',
                                    disk_owner,
                                    gw_metadata)

    def manage(self, desired_state):

        self.logger.debug("LUN.manage request for {}, desired state "
                          "{}".format(self.image, desired_state))

        if desired_state == 'present':

            self.allocate()

        elif desired_state == 'absent':

            self.remove_lun()


    def allocate_config(self):
        """
        Add disks info to config.
        """
        disk_list = RBDDev.rbd_list(pool=self.pool)
        self.logger.debug("rados pool '{}' contains the following - "
                          "{}".format(self.pool, disk_list))

        rbd_image = RBDDev(self.image, self.size, self.pool)
        self.pool_id = rbd_image.pool_id

        # if the image required isn't defined, create it!
        if self.image not in disk_list:
            # create the requested disk if this is the 'owning' host
           rbd_image.create()
           if rbd_image.error:
               self.error = True
               self.error_msg = rbd_image.error_msg

        self.logger.info("(LUN.allocate) created {}/{} "
                         "successfully".format(self.pool,self.image))
        # requested image is already defined to ceph
        if rbd_image.valid:
            # rbd image is OK to use, so ensure it's in the config object
            if self.config_key not in self.config.config['disks']:
                self.config.add_item('disks', self.config_key)
                self.owner = LUN.set_owner(self.config.config['gateways'])

                wwn = WWN()
                while wwn.formatted in self.config.config['disks']:
                    wwn = wwn.create()

                disk_attr = {"wwn": wwn.formatted,
                             "image": self.image,
                             "owner": self.owner,
                             "pool": self.pool,
                             "size": self.size,
                             "pool_id": self.pool_id,
                             "controls": self.controls }

                self.config.update_item('disks',
                                        self.config_key,
                                        disk_attr)

                gateway_dict = self.config.config['gateways'][self.owner]
                gateway_dict['active_luns'] += 1

                self.config.update_item('gateways',
                                        self.owner,
                                        gateway_dict)

        else:
                # rbd image is not valid for export, so abort
             self.error = True
             self.error_msg = ("(LUN.allocate) rbd '{}' is not compatible "
                               "with LIO\nOnly image features {} are"
                               " supported".format(self.image,
                               ','.join(RBDDev.rbd_feature_list)))
             self.logger.error(self.error_msg)


    def allocate_lio(self):
        wwn = self.config.config['disks'][self.config_key]['wwn']
        new_lun = self.add_dev_to_lio(wwn)
        if self.error:
            return
        # wwn = new_lun._get_wwn()
        #self.owner = LUN.set_owner(self.config.config['gateways'])
        self.logger.debug("{} owner will be {}".format(self.image,
                                                       self.owner))

        self.logger.debug("(LUN.allocate) registered '{}' to LIO "
                          "with wwn '{}' from the config "
                          "object".format(self.image, wwn))
        self.logger.info("(LUN.allocate) added '{}/{}' to LIO and"
                         " config object".format(self.pool, self.image))


    def allocate_resize(self):
        so = self.lio_stg_object()
        rbd_image = RBDDev(self.image, self.size, self.pool)
        if not self.lio_size_ok(rbd_image, so):
            self.error = True
            self.error_msg = "Unable to sync the rbd device size with LIO"
            self.logger.critical(self.error_msg)
            return

        self.logger.debug("config meta data for this disk is "
                          "{}".format(self.config.config['disks'][self.config_key]))


    def resize_config(self):
        rbd_image = RBDDev(self.image, self.size, self.pool)
        rbd_image.rbd_size()
        if rbd_image.error:
            self.logger.critical(rbd_image.error_msg)
            self.error = True
            self.error_msg = rbd_image.error_msg
            return

        if rbd_image.changed:
            self.logger.info("rbd image {} resized "
                             "to {}".format(self.config_key, self.size))

            disk_info = self.config.config['disks'][self.config_key]
            disk_info['size'] = self.size
            self.config.update_item('disks', self.config_key, disk_info)
        else:
            self.logger.debug("rbd image {} size matches the configuration"
                              " file request".format(self.config_key))


    def lio_size_ok(self, rbd_object, stg_object):
        """
        Check that the SO in LIO matches the current size of the rbd. if the
        size requested < current size, just return. Downsizing an rbd is not
        supported by this code and problematic for client filesystems anyway!
        :return boolean indicating whether the size matches
        """

        tmr = 0
        size_ok = False
        rbd_size_ok = False

        if self.size_bytes == rbd_object.current_size:
            rbd_size_ok = True

        # we have the right size for the rbd - check that LIO dev size matches
        if rbd_size_ok:

            # If the LIO size is not right, poke it with the new value
            if stg_object.size < self.size_bytes:
                self.logger.info("Resizing {} in LIO "
                                 "to {}".format(self.config_key,
                                                self.size_bytes))

                stg_object.set_attribute("dev_size", self.size_bytes)

                size_ok = stg_object.size == self.size_bytes

            else:
                size_ok = True

        return size_ok

    def lio_stg_object(self):
        found_it = False
        rtsroot = root.RTSRoot()
        for stg_object in rtsroot.storage_objects:

            # First match on name, but then check the pool incase the same
            # name exists in multiple pools
            if stg_object.name == self.config_key:

                found_it = True
                break

        return stg_object if found_it else None

    def add_dev_to_lio(self, in_wwn=None):
        """
        Add an rbd device to the LIO configuration
        :param in_wwn: optional wwn identifying the rbd image to clients
        (must match across gateways)
        :return: LIO LUN object
        """
        self.logger.info("(LUN.add_dev_to_lio) Adding image "
                         "'{}' to LIO".format(self.config_key))

        # extract control parameter overrides (if any) or use default
        controls = self.controls.copy()
        for k in ['max_data_area_mb']:
            if controls.get(k, None) is None:
                controls[k] = getattr(settings.config, k, None)

        control_string = gen_control_string(controls)
        if control_string:
            self.logger.debug("control=\"{}\"".format(control_string))

        new_lun = None
        try:
            # config string = rbd identifier / config_key (pool/image) /
            # optional osd timeout
            cfgstring = "rbd/{}/{};osd_op_timeout={}".format(self.pool,
                                         self.image,
                                         settings.config.osd_op_timeout)

            new_lun = UserBackedStorageObject(name=self.config_key,
                                              config=cfgstring,
                                              size=self.size_bytes,
                                              wwn=in_wwn, control=control_string)
        except RTSLibError as err:
            self.error = True
            self.error_msg = ("failed to add {} to LIO - "
                             "error({})".format(self.config_key,
                                                str(err)))
            self.logger.error(self.error_msg)
            return None

        try:
            new_lun.set_attribute("cmd_time_out", 0)
            new_lun.set_attribute("qfull_time_out",
                                  settings.config.qfull_timeout)
        except RTSLibError as err:
            self.error = True
            self.error_msg = ("Could not set LIO device attribute "
                             "cmd_time_out/qfull_time_out for device: {}. "
                             "Kernel not supported. - "
                             "error({})".format(self.config_key, str(err)))
            self.logger.error(self.error_msg)
            new_lun.delete()
            return None

        self.logger.info("(LUN.add_dev_to_lio) Successfully added {}"
                         " to LIO".format(self.config_key))

        return new_lun

    def remove_dev_from_lio(self):
        lio_root = root.RTSRoot()

        # remove the device from all tpgs
        for t in lio_root.tpgs:
            for lun in t.luns:
                if lun.storage_object.name == self.config_key:
                    try:
                        lun.delete()
                    except RTSLibError as e:
                        self.error = True
                        self.error_msg = ("Delete from LIO/TPG failed - "
                                          "{}".format(e))
                        return
                    else:
                        break       # continue to the next tpg

        for stg_object in lio_root.storage_objects:
            if stg_object.name == self.config_key:

                # alua_dir = os.path.join(stg_object.path, "alua")

                # # remove the alua directories (future versions will handle this
                # # natively within rtslib_fb
                # for dirname in next(os.walk(alua_dir))[1]:
                #     if dirname != "default_tg_pt_gp":
                #         try:
                #             alua_tpg = ALUATargetPortGroup(stg_object, dirname)
                #             alua_tpg.delete()
                #         except (RTSLibError, RTSLibNotInCFS) as err:
                #             self.error = True
                #             self.error_msg = ("Delete of ALUA dirs failed - "
                #                               "{}".format(err))
                #             return

                try:
                    stg_object.delete()
                except RTSLibError as e:
                    self.error = True
                    self.error_msg = ("Delete from LIO/backstores failed - "
                                      "{}".format(e))
                    return

                break

    @staticmethod
    def set_owner(gateways):
        """
        Determine the gateway in the configuration with the lowest number of
        active LUNs. This gateway is then selected as the owner for the
        primary path of the current LUN being processed
        :param gateways: gateway dict returned from the RADOS configuration
               object
        :return: specific gateway hostname (str) that should provide the
               active path for the next LUN
        """

        # Gateways contains simple attributes and dicts. The dicts define the
        # gateways settings, so first we extract only the dicts within the
        # main gateways dict
        gw_nodes = {key: gateways[key] for key in gateways
                    if isinstance(gateways[key], dict)}
        gw_items = gw_nodes.items()

        # first entry is the lowest number of active_luns
        gw_items.sort(key=lambda x: (x[1]['active_luns']))

        # 1st tuple is gw with lowest active_luns, so return the 1st
        # element which is the hostname
        return gw_items[0][0]


def rados_pool(conf=None, pool='rbd'):
    """
    determine if a given pool name is defined within the ceph cluster
    :param pool: pool name to check for (str)
    :return: Boolean representing the pool's existence
    """

    if conf is None:
        conf = settings.config.cephconf

    with rados.Rados(conffile=conf) as cluster:
        pool_list = cluster.list_pools()

    return pool in pool_list