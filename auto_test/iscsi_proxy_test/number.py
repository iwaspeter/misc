#!/usr/bin/env python

res = {}

def show_res(num):

    if num in res:
        return res[num]
    else:
        res[num] = []
        info = str(num)
        res[num].append(info)

    if num == 1:
        return ['1']
    for n in range(num - 1, 0, -1):
        other = num - n
        for r in  show_res(other):
            first_info = r.split('+')[0]
            if int(n) >= int(first_info):
                info = str(n) + '+' + r
                #print("push {} to res{}".format(info, num))
                res[num].append(info)

    return res[num]

if __name__ == '__main__':
    nums = range(10,11)
    for num in nums:
        print('begin {}'.format(num))
        show_res(num)
        print(res[num])
