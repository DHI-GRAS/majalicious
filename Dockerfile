FROM centos:7.2.1511
MAINTAINER Daniel Kristof <kristofdan@yahoo.com>

ARG http_proxy
ARG https_proxy
ARG ftp_proxy

ENV http_proxy "$http_proxy"
ENV https_proxy "$https_proxy"
ENV ftp_proxy "$ftp_proxy"

RUN yum -y update && yum -y install gd libxslt libxml2 git wget lbzip2 && yum clean all
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum clean all
RUN yum -y update && yum -y install python36u && yum clean all
 
RUN mkdir /usr/lbzip2 && cd /usr/lbzip2
RUN wget http://dl.fedoraproject.org/pub/epel/7/x86_64/Packages/l/lbzip2-2.5-1.el7.x86_64.rpm
RUN rpm -Uvh lbzip2-2.5-1.el7.x86_64.rpm

RUN mkdir /usr/local/maja && cd /usr/local/maja

ADD maja-1.0.0-rhel.7.2.x86_64-release-gcc.tar /usr/local/maja/
ADD maja-cots-1.0.0-rhel.7.2.x86_64-release-gcc.tar /usr/local/maja/

RUN cd /usr/local/maja/maja-cots-1.0.0-rhel.7.2.x86_64-release-gcc && echo 'Y'|./install.sh
RUN cd /usr/local/maja/maja-1.0.0-rhel.7.2.x86_64-release-gcc && echo 'Y'|./install.sh

ADD majalicious.py /usr/local/maja

RUN mkdir /maja-work-root

ENV MAJA_BIN "/opt/maja/core/1.0/bin/maja"

ENTRYPOINT ["python3.6", "/usr/local/maja/majalicious.py"]
CMD ["--help"] 
