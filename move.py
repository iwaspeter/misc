import copy
water = [8,0,0]
bott_size = [8,5,3]
cur_ops = []

def ret_ops(num):    
    ops = []
    for n in range(0, num):
        for m in range(0,num):
            if (n == m):
                continue
            ops.append([n,m])
    return ops

def get_res(water, ops):
    ret = []
    for op in ops:
        fr = op[0]
        to = op[1]
        if water[fr] == 0 or water[to] == bott_size[to]:
            continue

        ret.append(op)
    
    return ret

def min_size(s1,s2):
    if s1 > s2:
        return s2
    else:
        return s1

def print_res(op_list, last_op):
    op_len = len(op_list['ops'])
    for n in range(0, op_len):
        op = op_list['ops'][n]
        pwater = op_list['water'][n]
        print("{} --> {}: {}".format(op[0], op[1], pwater))
               
def done(water, ops, op_list):
    ret_ops = get_res(water, ops)
    for op in ret_ops:
        fr = op[0]
        to  = op[1]
        mywater=copy.copy(water)
        fr_size = mywater[fr]
        to_size = bott_size[to] -  mywater[to]
        real_size = min_size(fr_size, to_size)
        mywater[fr] -= real_size
        mywater[to]  += real_size
        if mywater in op_list['water']:
            continue

        if mywater == [4,4,0]:
            print_res(op_list, op)
            print("{} --> {}: {}".format(fr, to, mywater))
            print("==========================")
        else:
            op_list['water'].append(mywater)
            op_list['ops'].append(op)
            done(mywater, ops, op_list)
            op_list['water'].pop()
            op_list['ops'].pop()          

ops = ret_ops(3)
print(ops)
op_list = {}
op_list['water'] = []
op_list['ops'] = []
op_list['water'].append([8,0,0])
op_list['ops'].append([-1, 0])
done(water, ops, op_list)
