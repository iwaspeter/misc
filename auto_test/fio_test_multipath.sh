TMP=/tmp/multipath.tmp
DISKTMP=/tmp/disk.tmp
FIOTMP=/tmp/fio.tmp
FIOTEST=/tmp/test.tmp
rm -f $TMP
rm -f $DISKTMP
rm -f $FIOTMP
rm -f $FIOTEST

cat <<__EOF__ >> $FIOTEST
[global]
ioengine=libaio
thread=1
direct=1
buffered=0
rw=randrw
rwmixread=0
bs=4k
size=200G
iodepth=64
numjobs=1
runtime=1800
verify=md5
time_based
__EOF__

mkdir -p ./fio_test
cd fio_test
rm -f *
function show_disk()
{ 

    disk=$1
    disk_list=$(awk 'BEGIN{begin=0;pt=0;act=0}{if(pt==1){if($3~/sd/){print act "-" $3;exit};if($4 ~/sd/){print act "-" $4};if(act==1){act=0};pt=0};if(begin==1 && $0~/policy/){pt=1;if($NF~/active/){act=1}};if($1=="'$disk'"){begin=1};}' $TMP)
real_disk=$(readlink /dev/mapper/$disk)
for d in $disk_list
do 
   act=$(echo $d|awk -F '-' '{print $1}')
   dd=$(echo $d|awk -F '-' '{print $2}')
   disk_info=$(ls -l /dev/disk/by-path|awk '{if(substr($NF, 7) == "'$dd'"){split($9,info, "-");print info[2], "'$dd'"}}')
   #disk_info=$(ls -l /dev/disk/by-path|awk '{if(substr($NF, 7) == "'$dd'"){print $9;print "'$dd'" inf[1]}}')
   if [ "$act" -eq 1 ];then
       echo $disk_info $disk >>$DISKTMP
   #else
   #    echo $disk_info $disk $real_disk
   fi
done
}

function generate_fio_test()
{  
    size=$1
    iotype=$2
    seq_or_rand=$3
    disk_num=$4
    gw_num=$5
    per_gw_disk_num=$(($disk_num / $gw_num))
   
    if [ $iotype -eq 0 ];then
       type='write'
    elif [ $iotype -eq 100 ];then
       type='read'
    else
       type="r${iotype}w$((100 - $iotype))"
    fi

    test_name="${gw_num}gw_${disk_num}vol_${seq_or_rand}${type}_${size}.fio"
    cp -rf $FIOTEST  ./$test_name
    if [ $?  -ne 0 ];then
       echo "generate_fio_test() failed"
       exit
    fi 
    
   if [ $seq_or_rand == 'seq' ];then
       sed -i 's/rwmixread=/#rwmixread=/' $test_name
       sed -i "s/rw=.*$/rw=$type/" $test_name
       sed -i "s/^bs=.*$/bs=$size/" $test_name
       sed -i "s/iodepth=.*$/iodepth=8/" $test_name
   else
       sed -i "s/^bs=.*$/bs=$size/" $test_name
       sed -i "s/rwmixread=.*/rwmixread=$iotype/" $test_name
   fi

  awk 'BEGIN{need_print=0;gw_num=0} 
    { 
       if(gw_num >= "'$gw_num'"){
          ext=0
          for(g in gw_list) {
             if(gw_list[g] >= "'$per_gw_disk_num'") {ext++}
          }
          if(ext=="'$gw_num'"){exit}
       }
       if(NR % 2 != 0){ 
          split($0, array, "-"); gw=substr(array[1], 2); 
          if(gw_num == "'$gw_num'" && gw_list[gw] == 0){next}
          if(gw_list[gw] < "'$per_gw_disk_num'") {
              print $0;need_print=1;
              gg=gw
          } else { 
             need_print = 0;
          } 
       } else {
          if(need_print) {
             print $0
             if(gw_list[gg] == 0){gw_num+=1};
             gw_list[gg]++;
             need_print=0
          }
       }
    }' $FIOTMP >>$test_name 
   
   real_disk_num=$(cat $test_name |grep filename|wc -l)
   if [ $real_disk_num -lt $disk_num ];then
      rm -f $test_name
   fi
}

function do_test()
{
   
   local fn=$1
   local gn=$2
   
   local size=('4k' '1m') 
   local iotypes=(100 0 70)
   local seqrand=('rand' 'seq')
   
   for s in ${size[@]}
   do
       for it in ${iotypes[@]}
       do
          for sr in ${seqrand[@]}
          do
              if [ $s == '4k' -a $sr == 'seq' ];then
                 continue
              fi
              if [ $s == '1m' -a $sr == 'rand' ];then
                 continue
              fi
              if [ $s == '1m' -a "$it" -eq 70 ];then
                 continue
              fi
               
              generate_fio_test $s $it $sr $fn $gn
          done
       done
   done 
   
}

multipath -ll > $TMP

for disk in $(awk '{if($1~/mpath/){print $1}}' $TMP)
do
    show_disk $disk
done

if [ ! -f $DISKTMP ];then
   ls $DISKTMP
   exit
fi

num=1
cat $DISKTMP |sort |awk 'BEGIN{num=1}{print "["$1"-"num"]";print "filename=/dev/mapper/"$3;num+=1}' >$FIOTMP

filenum=$(cat $FIOTMP|grep 'filename='|wc -l)
gateway_num=$(cat $FIOTMP |awk '{if(NR % 2 != 0){split($0, array, "-"); gw=substr(array[1], 2);if(gw_list[gw] ==0){gw_num+=1;gw_list[gw]++}}}END{print gw_num}')

for fn in $(seq 1 $filenum)
do
   for gn in $(seq 1 $gateway_num)
   do
       if [ $fn -lt $gn ];then
          break
       fi
       do_test $fn $gn
   done
done 

rm -f $TMP
rm -f $DISKTMP
rm -f $FIOTMP
rm -f $FIOTEST
