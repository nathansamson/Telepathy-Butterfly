#!/usr/bin/env python

VERSION = '0.3.0'
APPNAME = 'telepathy-butterfly'

srcdir = '.'
blddir = '_build_'

import Scripting

Scripting.g_gz = 'bz2'
Scripting.g_excludes.extend(['pymsn', 'telepathy'])


def set_options(opt):
    opt.tool_options('python')
    opt.tool_options('gnu_dirs', 'tools')

def configure(conf):
    conf.check_tool('python misc')
    conf.check_tool('gnu_dirs', 'tools')

    conf.check_python_version()

    conf.define('VERSION', VERSION)
    conf.define('PACKAGE', APPNAME)

    print conf.env

def build(bld):
    bld.add_subdirs('butterfly data')
    install_files('LIBEXECDIR', '', 'telepathy-butterfly', chmod=0755)

