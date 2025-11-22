#!/bin/bash -xe
# /opt/aws/bin/cfn-init -v --stack '__STACK_ID__'
# --resource FeMasterInstance --region __REGION__

echo "vm.max_map_count=2000000" >> /etc/sysctl.conf
echo "vm.overcommit_memory=1" >> /etc/sysctl.conf
echo "fs.file-max=30000000" >> /etc/sysctl.conf
echo "fs.nr_open=20000000" >> /etc/sysctl.conf
echo "net.ipv4.tcp_keepalive_time=180" >> /etc/sysctl.conf
sysctl -p

if test -f /sys/kernel/mm/transparent_hugepage/enabled; then
    echo never > /sys/kernel/mm/transparent_hugepage/enabled
fi
if test -f /sys/kernel/mm/transparent_hugepage/defrag; then
    echo never > /sys/kernel/mm/transparent_hugepage/defrag
fi
echo "echo never > /sys/kernel/mm/transparent_hugepage/enabled" >> /etc/rc.local
echo "echo never > /sys/kernel/mm/transparent_hugepage/defrag" >> /etc/rc.local
sync

wget __JDK_DOWNLOAD_URL__ -O java.tar.gz
mkdir ./jdk && tar -zxvf java.tar.gz -C ./jdk --strip-components 1
mkdir /usr/java && mv jdk /usr/java
cat <<'EOF' >> /etc/profile
export JAVA_HOME=/usr/java/jdk
export JRE_HOME=/usr/java/jdk/jre
export CLASSPATH=.:/usr/java/jdk/lib:/usr/java/jdk/jre/lib:$CLASSPATH
export JAVA_PATH=/usr/java/jdk/bin:/usr/java/jdk/jre/bin
export PATH=$PATH:/usr/java/jdk/bin:/usr/java/jdk/jre/bin
EOF
source /etc/profile
rm -rf java.tar.gz

yum install -y MySQL-python.x86_64 mysql

useradd Doris || true
usermod -G Doris Doris || true

mkfs.xfs /dev/xvdt
mount /dev/xvdt /home/Doris || true
cd /home/Doris

mkdir -p /home/Doris/tool
cat <<'EOF' > /home/Doris/tool/addBeTool.py
#!/usr/bin/python
# -*- coding: UTF-8 -*-
import MySQLdb
import sys
import time
import os
time.sleep(30)
db = MySQLdb.connect(
    host='127.0.0.1',
    user='root',
    passwd='',
    port=9030,
    connect_timeout=10,
)
cursor = db.cursor()
for index in range(len(sys.argv)):
    if index == 0:
        continue
    if sys.argv[index] != '0.0.0.0':
        cursor.execute("ALTER SYSTEM ADD BACKEND '%s:9050'" % sys.argv[index])
data = cursor.fetchone()
db.close()
EOF
chmod +x /home/Doris/tool/addBeTool.py

wget __DORIS_DOWNLOAD_URL__ -O Doris.tar.gz
mkdir ./Doris && tar -zxvf Doris.tar.gz -C ./Doris --strip-components 1
rm -rf Doris.tar.gz

cd /home/Doris/Doris/fe
cat <<'EOF' > params.sh
#!/bin/bash
if [ $1 = "feDefaultMetaPath" ]; then
    mkdir -p meta
else
    mkdir -p $1
    sed -i "/^# meta_dir/ c\\meta_dir = $1" conf/fe.conf
fi
if [ $2 != "feDefaultLogPath" ]; then
    mkdir -p $2
    sed -i "/^LOG_DIR/ c\\LOG_DIR = $2" conf/fe.conf
    sed -i "/^# sys_log_dir/ c\\sys_log_dir = $2" conf/fe.conf
    sed -i "/^# audit_log_dir/ c\\audit_log_dir = $2" conf/fe.conf
fi
sed -i "/^sys_log_level/ c\\sys_log_level = $3" conf/fe.conf
EOF
chmod +x params.sh
bash params.sh __META_DIR__ __LOG_DIR__ __LOG_LEVEL__

chown -R Doris:Doris /home/Doris
ulimit -n 65536

bin/start_fe.sh --daemon

python /home/Doris/tool/addBeTool.py __BE_IP_ARGS__ >> addbe.log

/opt/aws/bin/cfn-signal -e $? \
    --stack __STACK_ID__ \
    --resource FeMasterInstance \
    --region __REGION__
