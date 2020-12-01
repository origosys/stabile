#!/usr/bin/env python
#
# Copyright (c) 2012 Cabo A/S
# All rights reserved.
#
# Written by Dan Villiom Podlaski Christiansen <dan@cabo.dk>
#

'''
Script and module for updating or combining a configuration file with
changes in a template.
'''

import itertools
import os
import sys

import configobj

def _readfile(path):
    ''' read the entire contents of 'path'. Equivalent to:

    >>> open(path).read()

    but without relying on reference counting to immediately close the file.
    '''
    with open(path) as fd:
        return fd.read()

def _removedups(lst):
    '''
    Return a copy of the list with all duplicates removed

    http://stackoverflow.com/a/6197827/136864
    '''
    dset = set()

    # relies on the fact that dset.add() always returns None.
    return [ l for l in lst if
             l not in dset and not dset.add(l) ]


def combineconfig(config, template):
    '''
    update the given config with new entries (and comments) from the
    template
    '''

    template = configobj.ConfigObj(template.splitlines())

    try:
        config = configobj.ConfigObj(config.splitlines(), raise_errors=True)
    except configobj.DuplicateError:
        config = \
            configobj.ConfigObj(_removedups(config.splitlines()))

    for key, value in config.items():
        if key not in template:
            template[key] = value
            template.comments[key] = config.comments[key] or ['']
            template.comments[key].append('# UNUSED!')
        else:
            template[key] = value

            if not template.comments[key] and any(config.comments[key]):
                template.comments[key] = config.comments[key]

    return template

def main(args):
    '''main entry point'''

    try:
        if len(args) != 3 and len(args) != 4:
            sys.stderr.write('usage: %s <config> <template> [dest]\n' %
                             os.path.basename(args[0]))
            return 1

        configpath = args[1]
        templatepath = args[2]

        config = combineconfig(_readfile(configpath), _readfile(templatepath))

        if len(args) == 4:
            with open(args[3], 'w') as outfd:
                config.write(outfd)
        else:
            config.write(sys.stdout)

        return 0
    except Exception as e:
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
