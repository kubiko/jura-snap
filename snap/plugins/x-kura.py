# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015 Canonical Ltd
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# This plugin is customised maven plugin for kura project.

import glob
import logging
import os
from urllib.parse import urlparse
from xml.etree import ElementTree
from urllib.parse import urlsplit

import snapcraft
import snapcraft.common
import snapcraft.plugins.maven
import snapcraft.plugins.ant

logger = logging.getLogger(__name__)


class KuraPlugin(snapcraft.plugins.maven.MavenPlugin):

    def __init__(self, name, options, project):
         super().__init__(name, options, project)
         if 'default-jdk' in self.stage_packages:
             self.stage_packages.remove('default-jdk')
         if 'openjdk-8-jdk' in self.stage_packages:
             self.stage_packages.remove('openjdk-8-jdk')
         if 'openjdk-9-jdk' in self.stage_packages:
             self.stage_packages.remove('openjdk-9-jdk')
         if 'openjdk-11-jdk' in self.stage_packages:
             self.stage_packages.remove('openjdk-11-jdk')
         self._maven_dir = os.path.join(self.partdir, "maven")

    def build(self):

        mvn_cmd = [ 'mvn' ]
        mvn_cmd += self.options.maven_options
        mvn_cmd += [ 'clean', 'install' ]

        if self._use_proxy():
            settings_path = os.path.join(self.partdir, 'm2', 'settings.xml')
            snapcraft.plugins.maven._create_settings(settings_path)
            mvn_cmd += ['-s', settings_path]
            mvn_cmd.extend(snapcraft.plugins.ant.AntPlugin.get_proxy_options(self, "http"))
            mvn_cmd.extend(snapcraft.plugins.ant.AntPlugin.get_proxy_options(self, "https"))

        self.run( [ 'java', '-version'],rootdir=self.builddir )
        logger.warning("maven params: mvn_cmd {}".format(mvn_cmd))
        for f in self.options.maven_targets:
            target  = os.path.join(f , 'pom.xml')
            self.run(mvn_cmd + [ '-f', target ], rootdir=self.builddir )

    def env(self, root):
        env = super().env(root)
        for index, e in enumerate(env[::-1]):
            if e.startswith('JAVA_HOME='):
                env.remove(e)
            if e.startswith('PATH='):
                env.remove(e)

        jars = glob.glob(os.path.join(self.installdir, "jar", "*.jar"))
        if jars:
            jars = [
                os.path.join(root, "jar", os.path.basename(x)) for x in sorted(jars)
            ]
            env.extend(["CLASSPATH={}:$CLASSPATH".format(":".join(jars))])

        stage_dir = os.path.join( os.path.dirname(os.path.dirname(os.path.dirname(self.installdir))), 'stage' )
        env.append( 'JAVA_HOME=%s/build-jdk/jre' % stage_dir )
        env.append( 'PATH=%s/build-jdk/jre/bin:%s/build-jdk/bin:$PATH' % (stage_dir, stage_dir) )
        return env

    def _build_environment(self):
        env = os.environ.copy()

        if env.get("SNAP"):
            env.pop("SNAP")
        if env.get("SNAP_NAME"):
            env.pop("SNAP_NAME")
        if env.get("SNAP_COMMON"):
            env.pop("SNAP_COMMON")
        if env.get("SNAP_DATA"):
            env.pop("SNAP_DATA")

        maven_bin = os.path.join(self._maven_dir, "bin")

        if env.get("PATH"):
            new_path = "{}:{}".format(maven_bin, env.get("PATH"))
        else:
            new_path = maven_bin

        if env.get("BUILD_JDK"):
            new_path = "{}:{}".format(env.get("BUILD_JDK"), new_path)

        env["PATH"] = new_path

        # Getting ant to use a proxy requires a little work; the JRE doesn't
        # help as much as it should.  (java.net.useSystemProxies=true ought
        # to do the trick, but it relies on desktop configuration rather
        # than using the standard environment variables.)
        ant_opts = []
        ant_opts.extend(snapcraft.plugins.ant.AntPlugin.get_proxy_options(self, "http"))
        ant_opts.extend(snapcraft.plugins.ant.AntPlugin.get_proxy_options(self, "https"))
        if ant_opts:
            env["ANT_OPTS"] = " ".join(opt.replace("'", "'\\''") for opt in ant_opts)
            env["ANT_ARGS"] = " ".join(opt.replace("'", "'\\''") for opt in ant_opts)
            env["JVM_OPTS"] = " ".join(opt.replace("'", "'\\''") for opt in ant_opts)
            env["JAVA_OPTS"] = " ".join(opt.replace("'", "'\\''") for opt in ant_opts)

        return env

    def enable_cross_compilation(self):
         pass

