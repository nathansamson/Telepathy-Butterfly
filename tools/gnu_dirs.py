#! /usr/bin/env python
# encoding: utf-8
# Ali Sabil, 2007

import Params
import Utils

import os.path

APPNAME = Utils.g_module.APPNAME
VERSION = Utils.g_module.VERSION


_options = (
        ('bindir', 'user executables', '$(EPREFIX)/bin'),
        ('sbindir', 'system admin executables', '$(EPREFIX)/sbin'),
        ('libexecdir', 'program executables', '$(EPREFIX)/libexec'),
        ('sysconfdir', 'read-only single-machine data', '$(PREFIX)/etc'),
        ('sharedstatedir', 'modifiable architecture-independent data', '$(PREFIX)/com'),
        ('localstatedir', 'modifiable single-machine data', '$(PREFIX)/var'),
        ('libdir', 'object code libraries', '$(EPREFIX)/lib'),
        ('includedir', 'C header files', '$(PREFIX)/include'),
        ('oldincludedir', 'C header files for non-gcc', '/usr/include'),
        ('datarootdir', 'read-only arch.-independent data root', '$(PREFIX)/share'),
        ('datadir', 'read-only architecture-independent data', '$(DATAROOTDIR)'),
        ('infodir', 'info documentation', '$(DATAROOTDIR)/info'),
        ('localedir', 'locale-dependent data', '$(DATAROOTDIR)/locale'),
        ('mandir', 'man documentation', '$(DATAROOTDIR)/man'),
        ('docdir', 'documentation root', '$(DATAROOTDIR)/doc/$(PACKAGE)'),
        ('htmldir', 'html documentation', '$(DOCDIR)'),
        ('dvidir', 'dvi documentation', '$(DOCDIR)'),
        ('pdfdir', 'pdf documentation', '$(DOCDIR)'),
        ('psdir', 'ps documentation', '$(DOCDIR)')
        )

_varprog = None
def _substitute_vars(path, vars):
    """Substitute variables in a path"""
    if '$' not in path:
        return path, 0

    global _varprog
    if not _varprog:
        import re
        _varprog = re.compile(r'\$(\w+|\([^)]*\))')

    i = 0
    unresolved_count = 0
    while True:
        m = _varprog.search(path, i)
        if m:
            i, j = m.span(0)
            name = m.group(1)
            if name[:1] == '(' and name[-1:] == ')':
                name = name[1:-1]
            if name in vars:
                tail = path[j:]
                path = path[:i] + vars[name]
                i = len(path)
                path = path + tail
            else:
                i = j
                unresolved_count += 1
        else:
            break
    return path, unresolved_count


def detect(conf):
    global _options, APPNAME, VERSION

    def get_param(varname):
            return getattr(Params.g_options, varname, '')

    conf.env['PREFIX'] = os.path.abspath(conf.env['PREFIX'])
    prefix = conf.env['PREFIX']

    eprefix = get_param('EPREFIX')
    if not eprefix:
        eprefix = prefix
    conf.env['EPREFIX'] = eprefix

    resolved_dirs_dict = {'PREFIX' : prefix, 'EPREFIX': eprefix,
            'APPNAME' : APPNAME, 'PACKAGE': APPNAME, 'VERSION' : VERSION}
    unresolved_dirs_dict = {}
    for name, help, default in _options:
        name = name.upper()
        value = get_param(name)
        if value:
            resolved_dirs_dict[name] = value
        else:
            unresolved_dirs_dict[name] = default

    while len(unresolved_dirs_dict) > 0:
        for name in unresolved_dirs_dict.keys():
            unresolved_path = unresolved_dirs_dict[name]
            path, count = _substitute_vars(unresolved_path, resolved_dirs_dict)
            if count == 0:
                resolved_dirs_dict[name] = path
                del unresolved_dirs_dict[name]
            else:
                unresolved_dirs_dict[name] = path

    del resolved_dirs_dict['APPNAME']
    del resolved_dirs_dict['PACKAGE']
    del resolved_dirs_dict['VERSION']
    for name, value in resolved_dirs_dict.iteritems():
        conf.env[name] = value

def set_options(opt):
    # copied from multisync-gui-0.2X wscript
    inst_dir = opt.add_option_group("Installation directories",
            'By default, waf install will install all the files in\
            "/usr/local/bin", "/usr/local/lib" etc.  You can specify \
            an installation prefix other than "/usr/local" using "--prefix",\
            for instance "--prefix=$HOME"')

    #just do some cleanups in the option list
    try:
        prefix_option = opt.parser.get_option("--prefix")
        opt.parser.remove_option("--prefix")
        destdir_option = opt.parser.get_option("--destdir")
        opt.parser.remove_option("--destdir")
        inst_dir.add_option(prefix_option)
        inst_dir.add_option(destdir_option)

    except:
        pass
    # end copy
    inst_dir.add_option('--exec-prefix',
            help="installation prefix [Default: %s]" % 'PREFIX',
	    default='',
	    dest='EPREFIX')

    dirs_options = opt.add_option_group("Fine tuning of the installation directories", '')

    global _options
    for name, help, default in _options:
        option_name = '--' + name
        str_default = default.replace('$(', '').replace(')', '')
        str_help = '%s [Default: %s]' % (help, str_default)
        dirs_options.add_option(option_name,
                help=str_help,
                default='',
                dest=name.upper())


