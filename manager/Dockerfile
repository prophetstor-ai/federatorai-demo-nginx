FROM centos:7.6.1810

ENV HOME ${APPHOME}
ENV APPHOME /opt/nginxdemo
ENV PATH ${APPHOME}:${PATH}

RUN set -x \
    ## Preparing OS
    && yum -y install epel-release \
    && yum install -y bind-utils \
    && yum install -y python-pip which httpd-tools python-yaml psmisc python2-devel gcc \
    ## install oc and kubectl
    && (mkdir -pv /usr/local/bin && cd /usr/local/bin && \
        curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/oc/4.4/linux/oc.tar.gz | gzip -dc | tar xvf - oc && \
        chmod 755 oc && ln -sfv oc kubectl)

COPY . /src
WORKDIR ${APPHOME}

RUN set -x \
    ## Generate version.txt
    && (cat /src/.git/FETCH_HEAD:aad3ec9efc31db69d81f5a9fac05ab7f3372f05d /src/.git/HEAD > version.txt 2>&1 || true) \
    ## install benchmark tools
    && sh -x /src/install.sh \
    && mkdir -pv ${APPHOME} \
    && mv -v /src/apps /src/config ${APPHOME} \
    && mv -v /src/*.py ${APPHOME} \
    && mv -v /src/transaction.txt ${APPHOME} \
    && mv -v /src/run.sh ${APPHOME} && chmod 755 ${APPHOME}/run.sh \
    && mv -v /src/cleanup.sh ${APPHOME} && chmod 755 ${APPHOME}/cleanup.sh \
    && cp -fv /src/manager/init.sh /init.sh && chmod 777 /init.sh \
    && chmod -R 777 ${APPHOME} \
    ## clean up
    && rm -rf /src \
    && yum clean all

CMD ["/init.sh"]
