#!/bin/bash -xe
# /opt/aws/bin/cfn-init -v --stack '__STACK_ID__'
# --resource __LOGICAL_ID__ --region __REGION__

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

wget __DORIS_DOWNLOAD_URL__ -O Doris.tar.gz
mkdir ./Doris && tar -zxvf Doris.tar.gz -C ./Doris --strip-components 1
rm -rf Doris.tar.gz

mkfs.xfs /dev/xvdh
mkdir -p /home/data
mount /dev/xvdh /home/data || true

cd /home/Doris/Doris/be
echo "storage_root_path = /home/data" >> conf/be.conf
echo 'JAVA_HOME=/usr/java/jdk' >> conf/be.conf
cat <<'EOF' > params.sh
#!/bin/bash
if [ $1 != "beDefaultLogPath" ]; then
    mkdir -p $1
    sed -i "/^# sys_log_dir/ c\\sys_log_dir = $1" conf/be.conf
fi
sed -i "/^sys_log_level/ c\\sys_log_level = $2" conf/be.conf
EOF
chmod +x params.sh
bash params.sh __BE_LOG_DIR__ __SYS_LOG_LEVEL__

chown -R Doris:Doris /home/Doris
ulimit -n 65536

bin/start_be.sh --daemon

/opt/aws/bin/cfn-signal -e $? \
    --stack __STACK_ID__ \
    --resource __LOGICAL_ID__ \
    --region __REGION__
