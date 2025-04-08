#!/bin/bash
file=$1
exists_true=0
exists_false=0
check_rslt_file=$2
if [ -f ${check_rslt_file} ]; then
    rm -f ${check_rslt_file}
else
    touch ${check_rslt_file}
fi

while read line; do
    filepath=`echo ${line}|awk -F, '{print $3}'`
    #echo $filepath
   if [ -f "${filepath}" ]; then
        echo "True,${line}" >>${check_rslt_file}
        exists_true=`expr $exists_true + 1`
    else
        echo "False,${line}" >>${check_rslt_file}
        exists_false=`expr $exists_false + 1`
    fi
done < ${file}

#echo "存在报告数：${exists_true}"
#echo "不存在报告数：${exists_false}"
echo "success"