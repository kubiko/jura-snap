# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
import os
import fileinput
import sys
import snapcraft
import logging
import shutil
import platform

from snapcraft.plugins import jdk, maven, dump
from snapcraft.internal import sources
from xml.etree import ElementTree

logger = logging.getLogger(__name__)

class OpenHabPlugin(snapcraft.BasePlugin):

    def __init__(self, name, options, project):
        super().__init__(name, options, project)
        self.build_packages.append('maven')
        self.jredir = os.path.join(self.partdir, 'jre')

    def _use_proxy(self):
        return any(k in os.environ for k in ('http_proxy', 'https_proxy'))

    def enable_cross_compilation(self):
        pass

    def build(self):
        snapcraft.BasePlugin.build(self)

        # mvn_cmd = ['mvn','-f','distributions/openhab/pom.xml', 'package']
        # mvn_cmd = ['./build-all.sh', '-Papu-debian', '\'-P!apu-debian-nn\'', '\'-P!beaglebone\''
        #           , '\'-P!beaglebone-nn\'', '\'-P!can\'', '\'-P!dev-env\'', '\'-P!dio.skip\''
        #           , '\'-P!extra-dps\'', '\'-P!fedora25\'', '\'-P!fedora25-nn\'', '\'-P!intel-edison\''
        #           , '\'-P!intel-edison-nn\'', '\'-P!raspberry-pi\'', '-Praspberry-pi-2-3'
        #           , '\'-P!raspberry-pi-2-3-nn\'', '\'-P!raspberry-pi-bplus\'', '\'-P!raspberry-pi-bplus-nn\''
        #           , '\'-P!raspberry-pi-nn\'', '\'-P!tools\'', '-Pweb', '\'-P!Win64-nn\'' ]
        mvn_cmd = ['./build-all.sh',
                   '-Papu-debian  -Pweb -Praspberry-pi-2-3 \'-P!apu-debian-nn\' \'-P!beaglebone\' \'-P!beaglebone-nn\' \'-P!can\' \'-P!dev-env\' \'-P!dio.skip\' \'-P!extra-dps\' \'-P!fedora25\' \'-P!fedora25-nn\' \'-P!intel-edison\' \'-P!intel-edison-nn\' \'-P!raspberry-pi\' \'-P!raspberry-pi-2-3-nn\' \'-P!raspberry-pi-bplus\' \'-P!raspberry-pi-bplus-nn\' \'-P!raspberry-pi-nn\' \'-P!tools\' \'-P!Win64-nn\'' ]

        if self._use_proxy():
            settings_path = os.path.join(self.partdir, 'm2', 'settings.xml')
            maven._create_settings(settings_path)
            mvn_cmd += ['-s', settings_path]

        if platform.machine() == 'armv7l':
            logger.warning('Setting up zulu jre for maven build')
            os.environ['JAVA_HOME'] = os.path.join(self.jredir, 'jre')
            os.environ['PATH'] = os.path.join(self.jredir, 'bin') + os.environ.get('PATH', 'not-set')

        self.run(mvn_cmd, self.sourcedir)

        tree = ElementTree.parse(os.path.join(self.sourcedir, 'kura/pom_pom.xml' ))
        root = tree.getroot()
        parent = root.find('{http://maven.apache.org/POM/4.0.0}project')
        version = parent.find('{http://maven.apache.org/POM/4.0.0}version').text

        dist_package = os.path.join(self.sourcedir, 'kura/distrib/target/kura_' + version + '_pcengines-apu.zip')

        sources.Zip(dist_package, self.builddir).pull()
        snapcraft.file_utils.link_or_copy_tree(
            self.builddir, self.installdir,
            copy_function=lambda src, dst: dump._link_or_copy(src, dst,
                                                         self.installdir))
    def pull(self):
        super().pull()
        if platform.machine() == 'armv7l':
            logger.warning('Running on armhf host, use zulu jre for maven')
            os.makedirs(self.jredir, exist_ok=True)
            class Options:
                source='https://www.azul.com/downloads/zulu/zdk-8-ga-linux_aarch32hf.tar.gz'

            snapcraft.sources.get(self.jredir, None, Options())
