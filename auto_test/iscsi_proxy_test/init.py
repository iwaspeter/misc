import rados
import rbd
from DiskTest from disk

def disk_create(pool, image, size):
    rbd_feature_list = ['RBD_FEATURE_LAYERING', 'RBD_FEATURE_EXCLUSIVE_LOCK',
                        'RBD_FEATURE_OBJECT_MAP', 'RBD_FEATURE_FAST_DIFF',
                        'RBD_FEATURE_DEEP_FLATTEN']

    with rados.Rados(conffile="/etc/ceph/ceph.conf") as cluster:
        with cluster.open_ioctx(pool) as ioctx:
            rbd_inst = rbd.RBD()
            try:
                rbd_inst.create(ioctx,
                        image,
                        size_bytes,
                `       features=rbd_feature_list,
                        old_format=False)

            except (rbd.ImageExists, rbd.InvalidArgument) as err:
                return "create error"

    return 'ok'

def pool_create(pool_name):
    with rados.Rados(conffile="/etc/ceph/ceph.conf") as cluster:
        try:
            ioctx = cluster.open_ioctx(pool_name):
            ioctx.close()
         except rados.ObjectNotFound:
            cluster.create_pool(pool_name)

def disk_init(table):
    disk_list = DiskTest.op_list()
    for disk in DiskTest.get_list()
        if disk  not in disk_list:
            continue
        else:
    table.insert()

def gwgroup_init():

def hostgroup_init():

def table_init():
